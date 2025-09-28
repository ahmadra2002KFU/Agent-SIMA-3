"""
Enhanced AI Data Analysis Application with Robust Architecture

This is the new version of the application that implements:
- Atomic response processing with validation
- Comprehensive error handling with circuit breakers
- Enhanced serialization for all pandas data types
- Graceful degradation without content corruption
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Import new architecture components
from server.response_manager import response_manager
from server.streaming_controller import streaming_controller
from server.error_handler import error_handler
from server.serialization_engine import serialization_engine
from server.validation_engine import validation_engine

# Import existing components
from server.lm_studio_client import lm_client
from server.code_executor import code_executor
from server.file_handler import file_handler
from server.metadata_extractor import metadata_extractor
from server.rules_manager import rules_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt for LLM
SYSTEM_PROMPT = """You are an expert data analyst AI assistant. Your task is to analyze data and provide insights through a structured 3-layer approach:

1. **Initial Analysis**: Understand the user's request and explain your approach
2. **Code Generation**: Generate Python code using the pre-loaded 'df' variable (NEVER use pd.read_csv)
3. **Results Commentary**: Interpret the results and provide actionable insights

CRITICAL REQUIREMENTS:
- Always use the pre-loaded 'df' variable for data access
- Never use file I/O operations like pd.read_csv(), open(), etc.
- Generate clean, executable Python code
- Provide clear explanations of your analysis

Respond in this exact JSON format:
{
    "initial_response": "Your analysis explanation here",
    "generated_code": "Python code here",
    "result_commentary": "Results interpretation here"
}"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Data Analysis Application v2.0")
    
    # Check LM Studio health
    lm_available = await lm_client.check_health()
    if lm_available:
        logger.info("✅ LM Studio connection established")
    else:
        logger.warning("⚠️ LM Studio not available - will use fallback responses")
    
    # Initialize system components
    logger.info("✅ Enhanced architecture components initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Data Analysis Application v2.0")
    await lm_client.close()


# Create FastAPI app with new architecture
app = FastAPI(
    title="AI Data Analysis Application v2.0",
    description="Enhanced data analysis with robust error handling and validation",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    """Serve the main application page."""
    return FileResponse("index.html")


@app.get("/health")
async def health_check():
    """Enhanced health check with component status."""
    system_health = error_handler.get_system_health()
    lm_available = await lm_client.check_health()
    
    return JSONResponse({
        "status": "healthy" if system_health["overall_health"] == "healthy" else "degraded",
        "version": "2.0.0",
        "lm_studio_available": lm_available,
        "system_health": system_health,
        "components": {
            "response_manager": "active",
            "validation_engine": "active",
            "serialization_engine": "active",
            "streaming_controller": "active",
            "error_handler": "active"
        }
    })


@app.get("/stats")
async def get_system_stats():
    """Get comprehensive system statistics."""
    return JSONResponse({
        "response_manager": response_manager.get_stats(),
        "streaming_controller": streaming_controller.get_stats(),
        "error_handler": error_handler.get_error_summary(),
        "serialization_engine": serialization_engine.get_stats(),
        "validation_engine": validation_engine.get_stats()
    })


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Upload and process data file with enhanced error handling."""
    try:
        # Use circuit breaker for file operations
        result = await error_handler.execute_with_circuit_breaker(
            "file_handler",
            _process_file_upload,
            file
        )
        return JSONResponse(result)
        
    except Exception as e:
        error_handler.record_error("file_upload", e, {"filename": file.filename})
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


async def _process_file_upload(file: UploadFile) -> Dict[str, Any]:
    """Process file upload with enhanced error handling."""
    # Save uploaded file
    file_path = await file_handler.save_uploaded_file(file)
    
    # Load and validate file
    success, message, dataframe = file_handler.load_file(file_path)
    if not success:
        raise Exception(f"File loading failed: {message}")
    
    # Extract metadata with enhanced serialization
    metadata = metadata_extractor.extract_metadata(dataframe, file.filename)
    
    # Serialize metadata safely
    serialized_metadata = serialization_engine.serialize_value(metadata)
    
    return {
        "status": "success",
        "message": message,
        "metadata": serialized_metadata
    }


@app.get("/file/metadata")
async def get_file_metadata() -> JSONResponse:
    """Get current file metadata with enhanced serialization."""
    try:
        metadata = file_handler.get_current_file_metadata()
        if metadata:
            # Use enhanced serialization
            serialized_metadata = serialization_engine.serialize_value(metadata)
            return JSONResponse({
                "status": "success",
                "metadata": serialized_metadata
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": "No file currently loaded"
            })
    except Exception as e:
        error_handler.record_error("file_metadata", e)
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")


@app.delete("/file")
async def clear_file() -> JSONResponse:
    """Clear the current uploaded file."""
    try:
        file_handler.clear_current_file()
        return JSONResponse({
            "status": "success",
            "message": "File cleared successfully"
        })
    except Exception as e:
        error_handler.record_error("file_clear", e)
        raise HTTPException(status_code=500, detail=f"File clear failed: {str(e)}")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    """Enhanced WebSocket endpoint with atomic response processing."""
    await ws.accept()
    
    try:
        while True:
            # Receive message
            raw = await ws.receive_text()
            try:
                payload: Dict[str, Any] = json.loads(raw)
            except Exception:
                payload = {"message": raw}
            
            user_msg = str(payload.get("message", ""))
            response_id = str(uuid.uuid4())
            
            # Send start event
            await streaming_controller._send_safe(ws, {"event": "start"})
            
            # Check LM Studio availability with circuit breaker
            try:
                lm_available = await error_handler.execute_with_circuit_breaker(
                    "lm_studio",
                    lm_client.check_health
                )
            except Exception:
                lm_available = False
            
            if lm_available:
                # Process with new architecture
                success = await _process_with_new_architecture(ws, response_id, user_msg)
                if not success:
                    # Fallback if processing fails
                    await streaming_controller.stream_fallback_response(
                        ws, user_msg, "Processing failed - using fallback"
                    )
            else:
                # LM Studio not available
                await streaming_controller.stream_fallback_response(
                    ws, user_msg, "LM Studio not available"
                )
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        return
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        error_handler.record_error("websocket", e)


async def _process_with_new_architecture(ws: WebSocket, response_id: str, user_msg: str) -> bool:
    """Process request using the new robust architecture."""
    try:
        # Create response generator
        response_generator = _create_response_generator(user_msg)
        
        # Process with response manager (atomic operations)
        processed_generator = response_manager.process_llm_response(
            response_id, response_generator
        )
        
        # Stream with streaming controller
        success = await streaming_controller.stream_response(
            ws, response_id, processed_generator
        )
        
        return success
        
    except Exception as e:
        logger.error(f"New architecture processing error: {e}", exc_info=True)
        error_handler.record_error("new_architecture", e, {"user_msg": user_msg})
        return False


async def _create_response_generator(user_msg: str):
    """Create response generator for the new architecture."""
    try:
        # Get file metadata and user rules
        file_metadata = file_handler.get_current_file_metadata()
        user_rules = rules_manager.get_rules_text()
        
        # Generate LLM response with circuit breaker protection
        async for response_chunk in lm_client.generate_structured_response(
            user_message=user_msg,
            system_prompt=SYSTEM_PROMPT,
            file_metadata=file_metadata,
            user_rules=user_rules,
            initial_response_temp=0.7,
            generated_code_temp=0.3,
            result_commentary_temp=0.2
        ):
            yield response_chunk
            
            # If we have generated code, execute it
            field = response_chunk.get("field")
            if field == "generated_code":
                content = response_chunk.get("content", "")
                if content.strip():
                    # Execute code with circuit breaker protection
                    try:
                        execution_results = await error_handler.execute_with_circuit_breaker(
                            "code_executor",
                            _execute_code_safely,
                            content
                        )
                        
                        # Add execution results to the response
                        yield {
                            "field": "execution_results",
                            "content": execution_results
                        }
                        
                    except Exception as e:
                        logger.error(f"Code execution error: {e}", exc_info=True)
                        error_handler.record_error("code_execution", e)
                        
                        yield {
                            "field": "execution_error",
                            "content": f"Code execution failed: {str(e)}"
                        }
    
    except Exception as e:
        logger.error(f"Response generation error: {e}", exc_info=True)
        error_handler.record_error("response_generation", e)
        
        # Yield error response
        yield {
            "field": "initial_response",
            "content": f"Error generating response: {str(e)}"
        }
        yield {
            "field": "generated_code",
            "content": "# Error occurred during code generation"
        }
        yield {
            "field": "result_commentary",
            "content": "Unable to process request due to system error."
        }


async def _execute_code_safely(code: str) -> Dict[str, Any]:
    """Execute code safely with enhanced serialization."""
    # Get current dataframe
    current_file = file_handler.current_file
    dataframe = current_file['dataframe'] if current_file else None
    
    # Execute code
    success, output, results = code_executor.execute_code(code, dataframe)
    
    # Enhanced serialization of results
    if results:
        serialized_results = serialization_engine.serialize_execution_results(results)
    else:
        serialized_results = "{}"
    
    return {
        "success": success,
        "output": output,
        "results": results,
        "serialized_results": serialized_results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010, reload=True)
