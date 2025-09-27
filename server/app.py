import asyncio
import json
import logging
import math
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from lm_studio_client import lm_client
from file_handler import file_handler
from code_executor import code_executor
from rules_manager import rules_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("AI Sima Chatbot server starting up...")

    # Auto-load hospital_patients.csv if it exists
    hospital_file_path = "../uploads/hospital_patients.csv"
    if os.path.exists(hospital_file_path):
        logger.info(f"Auto-loading {hospital_file_path}...")
        success = file_handler.set_current_file(hospital_file_path, "hospital_patients.csv")
        if success:
            file_info = file_handler.get_current_file_info()
            logger.info(f"Successfully loaded hospital_patients.csv: {file_info['rows']} rows, {file_info['columns']} columns")
        else:
            logger.warning("Failed to auto-load hospital_patients.csv")

    yield
    # Shutdown
    logger.info("AI Sima Chatbot server shutting down...")
    await lm_client.close()
    file_handler.clear_current_file()


app = FastAPI(title="Local LLM Chatbot (POC)", lifespan=lifespan)

# System prompt for the LLM
SYSTEM_PROMPT = """You are an AI assistant specialized in data analysis and visualization.
You help users analyze their data files (CSV, XLSX) and create insights through code generation and execution.

CRITICAL RULES FOR CODE GENERATION:
- NEVER use pd.read_csv() or try to read files from disk
- ALWAYS use the variable 'df' which contains the already-loaded uploaded data
- The uploaded file is pre-processed and available as 'df' - do not attempt to load it again
- If you need to reference the data, use 'df' directly

When responding to user queries:
1. First provide an initial response explaining what you plan to do
2. Generate Python code if needed for analysis/visualization (ALWAYS use 'df' for data, never pd.read_csv)
3. Provide commentary on results in natural language

You have access to pandas, plotly, numpy, and other data analysis libraries.
Focus on creating high-quality, interactive visualizations when requested.

EXAMPLE of correct code:
```python
# CORRECT - use the pre-loaded dataframe
saudi_patients = df[df['Nationality'].str.contains('Saudi', case=False, na=False)]
count = len(saudi_patients)
```

NEVER do this:
```python
# WRONG - do not try to read files
df = pd.read_csv('filename.csv')  # This will fail!
```"""


@app.get("/")
async def root_index() -> FileResponse:
    # Serve the existing frontend file
    return FileResponse("../index.html")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Handle file upload."""
    try:
        # Read file content
        file_content = await file.read()

        # Save the uploaded file
        success, message, file_path = await file_handler.save_uploaded_file(
            file.filename, file_content
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        # Set as current file
        if not file_handler.set_current_file(file_path, file.filename):
            raise HTTPException(status_code=500, detail="Failed to process uploaded file")

        # Get file info
        file_info = file_handler.get_current_file_info()

        return JSONResponse({
            "status": "success",
            "message": message,
            "file_info": file_info
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/file-info")
async def get_file_info() -> JSONResponse:
    """Get information about the current uploaded file."""
    file_info = file_handler.get_current_file_info()

    if not file_info:
        return JSONResponse({
            "status": "no_file",
            "message": "No file currently uploaded"
        })

    return JSONResponse({
        "status": "success",
        "file_info": file_info
    })


@app.get("/file-metadata")
async def get_file_metadata() -> JSONResponse:
    """Get comprehensive metadata about the current uploaded file."""
    metadata = file_handler.get_current_file_metadata()

    if not metadata:
        return JSONResponse({
            "status": "no_file",
            "message": "No file currently uploaded"
        })

    return JSONResponse({
        "status": "success",
        "metadata": metadata
    })


@app.post("/execute-code")
async def execute_code(request: dict) -> JSONResponse:
    """Execute Python code in a sandboxed environment."""
    try:
        code = request.get("code", "")
        if not code:
            raise HTTPException(status_code=400, detail="No code provided")

        # Validate code
        is_safe, error_msg = code_executor.validate_code(code)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"Code validation failed: {error_msg}")

        # Get current dataframe if available
        current_file = file_handler.current_file
        dataframe = current_file['dataframe'] if current_file else None

        # Execute code
        success, output, results = code_executor.execute_code(code, dataframe)

        # Clean the response data to handle NaN values
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, float):
                if math.isnan(obj):
                    return None
                elif math.isinf(obj):
                    return "Infinity" if obj > 0 else "-Infinity"
                else:
                    return obj
            else:
                return obj

        response_data = {
            "status": "success" if success else "error",
            "output": output,
            "results": clean_for_json(results),
            "has_dataframe": dataframe is not None
        }

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@app.get("/rules")
async def get_rules(category: str = None) -> JSONResponse:
    """Get all rules, optionally filtered by category."""
    try:
        rules = rules_manager.get_rules(category=category)
        stats = rules_manager.get_stats()

        return JSONResponse({
            "status": "success",
            "rules": rules,
            "stats": stats
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")


@app.post("/rules")
async def add_rule(request: dict) -> JSONResponse:
    """Add a new rule."""
    try:
        rule_text = request.get("text", "").strip()
        if not rule_text:
            raise HTTPException(status_code=400, detail="Rule text is required")

        category = request.get("category", "general")
        priority = request.get("priority", 1)

        rule = rules_manager.add_rule(rule_text, category, priority)

        return JSONResponse({
            "status": "success",
            "message": "Rule added successfully",
            "rule": rule
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add rule: {str(e)}")


@app.put("/rules/{rule_id}")
async def update_rule(rule_id: int, request: dict) -> JSONResponse:
    """Update an existing rule."""
    try:
        updated_rule = rules_manager.update_rule(rule_id, **request)

        if not updated_rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        return JSONResponse({
            "status": "success",
            "message": "Rule updated successfully",
            "rule": updated_rule
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")


@app.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int) -> JSONResponse:
    """Delete a rule."""
    try:
        success = rules_manager.delete_rule(rule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")

        return JSONResponse({
            "status": "success",
            "message": "Rule deleted successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


@app.post("/rules/import")
async def import_rules(request: dict) -> JSONResponse:
    """Import rules from text."""
    try:
        rules_text = request.get("text", "")
        category = request.get("category", "imported")

        if not rules_text:
            raise HTTPException(status_code=400, detail="Rules text is required")

        imported_count = rules_manager.import_rules_from_text(rules_text, category)

        return JSONResponse({
            "status": "success",
            "message": f"Imported {imported_count} rules successfully",
            "imported_count": imported_count
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import rules: {str(e)}")


@app.delete("/file")
async def clear_file() -> JSONResponse:
    """Clear the current uploaded file."""
    file_handler.clear_current_file()
    return JSONResponse({
        "status": "success",
        "message": "File cleared successfully"
    })


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            # Expect a JSON message from the client like {"message": "Hi"}
            raw = await ws.receive_text()
            try:
                payload: Dict[str, Any] = json.loads(raw)
            except Exception:
                payload = {"message": raw}

            user_msg = str(payload.get("message", ""))

            # Check if LM Studio is available
            lm_available = await lm_client.check_health()

            await ws.send_json({"event": "start"})

            if lm_available:
                # Use LM Studio for response generation with 3-layer architecture
                try:
                    field_content = {"initial_response": "", "generated_code": "", "result_commentary": ""}

                    # Get file metadata if available
                    file_metadata = file_handler.get_current_file_metadata()

                    # Get user rules
                    user_rules = rules_manager.get_rules_text()

                    # Step 1: Generate initial response and code
                    await ws.send_json({"event": "delta", "field": "initial_response", "delta": "Analyzing your request and generating response..."})

                    async for response_chunk in lm_client.generate_structured_response(
                        user_message=user_msg,
                        system_prompt=SYSTEM_PROMPT,
                        file_metadata=file_metadata,
                        user_rules=user_rules,
                        initial_response_temp=0.7,
                        generated_code_temp=0.3,
                        result_commentary_temp=0.2
                    ):
                        field = response_chunk.get("field")
                        content = response_chunk.get("content", "")

                        if field and field in field_content:
                            field_content[field] = content

                            # Stream the content in chunks for initial_response and generated_code
                            if field in ["initial_response", "generated_code"]:
                                for i in range(0, len(content), 8):
                                    chunk = content[i:i+8]
                                    await ws.send_json({"event": "delta", "field": field, "delta": chunk})
                                    await asyncio.sleep(0.02)

                    # Step 2: Execute generated code if any
                    execution_results = None
                    if field_content.get("generated_code", "").strip():
                        await ws.send_json({"event": "delta", "field": "result_commentary", "delta": "Executing generated code..."})

                        # Get current dataframe if available
                        current_file = file_handler.current_file
                        dataframe = current_file['dataframe'] if current_file else None

                        # Execute the code
                        success, output, results = code_executor.execute_code(
                            field_content["generated_code"],
                            dataframe
                        )

                        execution_results = {
                            "success": success,
                            "output": output,
                            "results": results
                        }

                        # Add execution results to field_content for final response
                        field_content["execution_results"] = execution_results
                        if results:
                            field_content["results"] = results

                        # Send execution status
                        status_msg = "Code executed successfully. " if success else f"Code execution failed: {output[:100]}... "
                        await ws.send_json({"event": "delta", "field": "result_commentary", "delta": status_msg})

                    # Step 3: Generate commentary based on execution results
                    if execution_results:
                        commentary_prompt = f"Provide natural language interpretation of the following code execution results: {json.dumps(execution_results, indent=2)}"

                        async for response_chunk in lm_client.generate_structured_response(
                            user_message=commentary_prompt,
                            system_prompt="You are an expert data analyst. Interpret code execution results and provide clear, actionable insights. Be concise and factual.",
                            code_execution_results=execution_results,
                            user_rules=user_rules,
                            initial_response_temp=0.5,
                            generated_code_temp=0.3,
                            result_commentary_temp=0.1
                        ):
                            field = response_chunk.get("field")
                            content = response_chunk.get("content", "")

                            if field == "result_commentary":
                                field_content["result_commentary"] = content
                                # Stream the commentary
                                for i in range(0, len(content), 8):
                                    chunk = content[i:i+8]
                                    await ws.send_json({"event": "delta", "field": "result_commentary", "delta": chunk})
                                    await asyncio.sleep(0.02)
                    else:
                        # No code execution, use the original commentary
                        commentary = field_content.get("result_commentary", "")
                        for i in range(0, len(commentary), 8):
                            chunk = commentary[i:i+8]
                            await ws.send_json({"event": "delta", "field": "result_commentary", "delta": chunk})
                            await asyncio.sleep(0.02)

                    # Send final assembled object
                    await ws.send_json({
                        "event": "end",
                        "final": field_content
                    })

                except Exception as e:
                    # Fallback to stub response if LM Studio fails
                    await _send_fallback_response(ws, user_msg, f"LM Studio error: {str(e)}")
            else:
                # Fallback to stub response if LM Studio is not available
                await _send_fallback_response(ws, user_msg, "LM Studio not available")

    except WebSocketDisconnect:
        # Client disconnected; simply return
        return


async def _send_fallback_response(ws: WebSocket, user_msg: str, error_msg: str = "") -> None:
    """Send a fallback response when LM Studio is not available."""
    async def stream_field(field: str, text: str, delay: float = 0.05) -> None:
        for i in range(0, len(text), 8):
            await ws.send_json({"event": "delta", "field": field, "delta": text[i:i+8]})
            await asyncio.sleep(delay)

    initial = f"I received your message: '{user_msg}'. {error_msg}"
    code = (
        "# Fallback response - LM Studio integration needed\n"
        "# This is a placeholder demonstration\n"
        "print('Hello from the chatbot!')\n"
    )
    commentary = "This is a fallback response. Please ensure LM Studio is running on http://127.0.0.1:1234"

    await stream_field("initial_response", initial)
    await stream_field("generated_code", code)
    await stream_field("result_commentary", commentary)

    await ws.send_json({
        "event": "end",
        "final": {
            "initial_response": initial,
            "generated_code": code,
            "result_commentary": commentary,
        },
    })


# Lifespan events are now handled in the lifespan context manager above


if __name__ == "__main__":
    # Run the dev server
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010, reload=True)

