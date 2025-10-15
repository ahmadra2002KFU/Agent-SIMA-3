import asyncio
import json
import logging
import math
from contextlib import asynccontextmanager
from typing import Any, Dict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from lm_studio_client import lm_client
from file_handler import file_handler
from code_executor import code_executor
from rules_manager import rules_manager

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"
INDEX_FILE = PROJECT_ROOT / "index.html"
UPLOADS_DIR = PROJECT_ROOT / "uploads"

CONTEXT_TRUNCATION_SUFFIX = "... [truncated]"
ANALYSIS_SECTION_LIMIT = 2000
CODE_SECTION_LIMIT = 6000
OUTPUT_SECTION_LIMIT = 2000
RESULT_SECTION_LIMIT = 2000

def _truncate_for_context(value: Any, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + CONTEXT_TRUNCATION_SUFFIX

def _stringify_for_context(value: Any, limit: int) -> str:
    if isinstance(value, (dict, list)):
        try:
            text_value = json.dumps(value, indent=2, default=str)
        except Exception:
            text_value = str(value)
    else:
        text_value = str(value)
    return _truncate_for_context(text_value, limit)

def _sanitize_execution_results_for_commentary(execution_results: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(execution_results, dict):
        return {}
    sanitized: Dict[str, Any] = {}
    if "success" in execution_results:
        sanitized["success"] = execution_results.get("success")
    output_value = execution_results.get("output")
    if output_value:
        sanitized["output"] = _stringify_for_context(output_value, OUTPUT_SECTION_LIMIT)
    results = execution_results.get("results")
    if isinstance(results, dict):
        summarized_results: Dict[str, Any] = {}
        for key, value in results.items():
            if isinstance(value, dict) and value.get("type") == "plotly_figure":
                summarized_results[key] = {
                    "note": "Plotly figure omitted from commentary context to keep prompt concise."
                }
            else:
                summarized_results[key] = _stringify_for_context(value, RESULT_SECTION_LIMIT)
        if summarized_results:
            sanitized["results"] = summarized_results
    executed_code = execution_results.get("executed_code")
    if executed_code:
        sanitized["executed_code"] = _stringify_for_context(executed_code, CODE_SECTION_LIMIT)
    return sanitized

def _format_execution_summary(execution_results: Dict[str, Any]) -> str:
    if not execution_results:
        return "No execution results available."
    lines = []
    success = execution_results.get("success")
    if success is not None:
        lines.append(f"Status: {'Success' if success else 'Failed'}")
    output = execution_results.get("output")
    if output:
        lines.append("Console Output:")
        lines.append(output)
    results = execution_results.get("results")
    if isinstance(results, dict) and results:
        lines.append("Captured Results:")
        for key, value in results.items():
            if isinstance(value, dict) and value.get("note"):
                note = value.get("note")
                lines.append(f"- {key}: {note}")
            else:
                lines.append(f"- {key}: {value}")
    else:
        lines.append("Captured Results: None")
    return "\n".join(lines)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("AI Sima Chatbot server starting up...")

    # Auto-load hospital_patients.csv if it exists
    hospital_file_path = UPLOADS_DIR / "hospital_patients.csv"
    if hospital_file_path.exists():
        logger.info(f"Auto-loading {hospital_file_path}...")
        success = file_handler.set_current_file(str(hospital_file_path), "hospital_patients.csv")
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

# Mount static files to serve the logo
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# System prompt for the LLM
SYSTEM_PROMPT = """You are an AI assistant specialized in data analysis and visualization.
You help users analyze their data files (CSV, XLSX) and create insights through code generation and execution.

CRITICAL RULES FOR CODE GENERATION:
- NEVER use pd.read_csv() or try to read files from disk
- ALWAYS use the variable 'df' which contains the already-loaded uploaded data
- The uploaded file is pre-processed and available as 'df' - do not attempt to load it again
- If you need to reference the data, use 'df' directly
- IMPORTANT: ALWAYS assign your final output/results to a variable named 'result' or 'output'
- For visualizations, assign the figure to 'fig' or 'figure'
- Always use plotly instead of matplotlib
- Never use matplotlib under any circumstance

RESPONSE STRUCTURE - Generate in this order:
1. **Generate Python code FIRST** - Write the code to solve the user's query
   - Use 'df' for the pre-loaded data
   - Assign final output to 'result', 'output', or 'fig'/'figure' for visualizations
   - Keep code clean, efficient, and well-commented

2. **Provide analysis/explanation SECOND** - Explain your approach and methodology
   - Describe what the code does and why
   - Explain the analytical approach taken
   - Mention any assumptions or data transformations

3. **Commentary on results** - This will be generated after code execution
   - Interpret the results in context of the user's question
   - Provide insights and additional context
   - Highlight key findings

You have access to pandas, plotly, numpy, and other data analysis libraries.
Focus on creating high-quality, interactive visualizations when requested.

EXAMPLES of correct code:
```python
# CORRECT - use the pre-loaded dataframe and assign to result
saudi_patients = df[df['Nationality'].str.contains('Saudi', case=False, na=False)]
result = len(saudi_patients)
```

```python
# CORRECT - for showing data
result = df.head(5)
```

```python
# CORRECT - for multiple results
admissions_by_year = df.groupby('year').size()
percent_change = calculate_change(admissions_by_year)
result = {'admissions': admissions_by_year, 'change': percent_change}
```

```python
# CORRECT - for visualizations
import plotly.express as px
fig = px.bar(df.groupby('Nationality').size().reset_index(name='count'),
             x='Nationality', y='count', title='Patient Distribution by Nationality')
```

NEVER do this:
```python
# WRONG - do not try to read files
df = pd.read_csv('filename.csv')  # This will fail!

# WRONG - no result variable assigned
df.head(5)  # This won't capture the output!
```"""


@app.get("/")
async def root_index() -> FileResponse:
    # Serve the existing frontend file
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/health/lmstudio")
async def health_lmstudio() -> JSONResponse:
    """Check LM Studio health status."""
    is_healthy = await lm_client.check_health()
    return JSONResponse({
        "status": "ok" if is_healthy else "unavailable",
        "lm_studio": {
            "running": is_healthy,
            "url": lm_client.base_url
        }
    })


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

        # Enhanced validation with auto-fix (now integrated into execute_code)
        # Basic security validation first
        is_safe, error_msg = code_executor.validate_code(code)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"Code validation failed: {error_msg}")

        # Get current dataframe if available
        current_file = file_handler.current_file
        dataframe = current_file['dataframe'] if current_file else None

        # Execute code with enhanced validation and auto-fix
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
                    # Track how many characters have been streamed per field to avoid re-sending
                    last_sent_len = {"initial_response": 0, "generated_code": 0, "result_commentary": 0}

                    # Get file metadata if available
                    file_metadata = file_handler.get_current_file_metadata()

                    # Get user rules
                    user_rules = rules_manager.get_rules_text()

                    # Step 1: Generate initial response and code
                    await ws.send_json({"event": "status", "field": "initial_response", "status": "analyzing"})

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

                            # Stream only the newly added delta for initial_response and generated_code
                            if field in ["initial_response", "generated_code"]:
                                start = last_sent_len[field]
                                if start < len(content):
                                    delta = content[start:]
                                    for i in range(0, len(delta), 8):
                                        chunk = delta[i:i+8]
                                        await ws.send_json({"event": "delta", "field": field, "delta": chunk})
                                        await asyncio.sleep(0.02)
                                    last_sent_len[field] = len(content)

                    # Step 2: Execute generated code if any
                    execution_results = None
                    if field_content.get("generated_code", "").strip():
                        # Removed status message - skeleton loader handles visual feedback
                        # await ws.send_json({"event": "delta", "field": "result_commentary", "delta": "Executing generated code..."})

                        # Get current dataframe if available
                        current_file = file_handler.current_file
                        dataframe = current_file['dataframe'] if current_file else None

                        # Execute the code
                        try:
                            success, output, results = code_executor.execute_code(
                                field_content["generated_code"],
                                dataframe
                            )

                            execution_results = {
                                "success": success,
                                "output": output,
                                "results": results,
                                "executed_code": field_content["generated_code"]  # Include the actual code that was executed
                            }

                            # Removed status message - skeleton loader handles visual feedback
                            # status_msg = "Code executed successfully. " if success else f"Code execution failed: {output[:100]}... "
                            # await ws.send_json({"event": "delta", "field": "result_commentary", "delta": status_msg})
                        except Exception as e:
                            logger.error(f"Code execution error: {str(e)}", exc_info=True)
                            execution_results = {
                                "success": False,
                                "output": f"Code execution error: {str(e)}",
                                "results": None,
                                "executed_code": field_content["generated_code"]  # Include the code even if execution failed
                            }
                            await ws.send_json({"event": "delta", "field": "result_commentary", "delta": f"Code execution failed: {str(e)[:100]}... "})

                    # Step 3: Generate commentary based on execution results
                    if execution_results:
                        sanitized_execution_results = _sanitize_execution_results_for_commentary(execution_results)
                        execution_summary_text = _format_execution_summary(sanitized_execution_results)
                        analysis_summary = _truncate_for_context(field_content.get("initial_response", ""), ANALYSIS_SECTION_LIMIT)
                        if not analysis_summary:
                            analysis_summary = "No analysis summary available."

                        code_for_prompt = sanitized_execution_results.get("executed_code") or field_content.get("generated_code", "").strip()
                        if code_for_prompt:
                            code_for_prompt = _truncate_for_context(code_for_prompt, CODE_SECTION_LIMIT)
                        else:
                            code_for_prompt = "# No code generated."

                        prompt_parts = [
                            "Interpret the analysis results for the user.",
                            "",
                            f'ORIGINAL USER QUERY: "{user_msg}"',
                            "",
                            "ANALYSIS SUMMARY:",
                            analysis_summary,
                            "",
                            "GENERATED CODE:",
                            "```python",
                            code_for_prompt,
                            "```",
                            "",
                            "EXECUTION SUMMARY:",
                            execution_summary_text,
                            "",
                            "COMMENTARY INSTRUCTIONS:",
                            "1. Start with the direct answer to the user's question.",
                            "2. Explain the methodology by referencing the code and outputs.",
                            "3. Provide relevant context or next steps based on the findings.",
                            "4. If a visualization was generated, describe its key takeaway using the execution summary (raw figure data is omitted).",
                        ]
                        commentary_prompt = "\n".join(prompt_parts)

                        async for response_chunk in lm_client.generate_structured_response(
                            user_message=commentary_prompt,
                            system_prompt="""You are an expert data analyst. Interpret code execution results by answering the user's ORIGINAL QUERY first, using the primary result in the correct context.

CRITICAL COMMENTARY STRUCTURE:
1. **ANSWER THE ORIGINAL QUERY**: Use the primary result to directly answer what the user asked
2. **METHODOLOGY EXPLANATION**: Explain how the code achieved this result
3. **TECHNICAL DETAILS**: Reference specific functions, operations, or techniques used
4. **CONTEXTUAL INSIGHTS**: Provide relevant additional insights

EXAMPLE for "What is the average age of American patients?":
"The average age of American patients is 54.8 years. The code calculated this by filtering for patients with 'American' nationality and using a custom age calculation function that computed age at admission by comparing Date_of_Birth with Admission_Date, accounting for whether the birthday had occurred yet in the admission year."

CRITICAL: The primary result must be interpreted in the context of the original user query. If the user asks for "average age", the result represents age in years, not a percentage or count.""",
                            code_execution_results=sanitized_execution_results,
                            user_rules=user_rules,
                            initial_response_temp=0.5,
                            generated_code_temp=0.3,
                            result_commentary_temp=0.1
                        ):
                            field = response_chunk.get("field")
                            content = response_chunk.get("content", "")

                            if field == "result_commentary":
                                field_content["result_commentary"] = content
                                # Stream only the newly added portion of the commentary
                                start = last_sent_len["result_commentary"]
                                if start < len(content):
                                    delta = content[start:]
                                    for i in range(0, len(delta), 8):
                                        chunk = delta[i:i+8]
                                        await ws.send_json({"event": "delta", "field": "result_commentary", "delta": chunk})
                                        await asyncio.sleep(0.02)
                                    last_sent_len["result_commentary"] = len(content)
                    else:
                        # No code execution, use the original commentary
                        commentary = field_content.get("result_commentary", "")
                        start = last_sent_len["result_commentary"]
                        if start < len(commentary):
                            delta = commentary[start:]
                            for i in range(0, len(delta), 8):
                                chunk = delta[i:i+8]
                                await ws.send_json({"event": "delta", "field": "result_commentary", "delta": chunk})
                                await asyncio.sleep(0.02)
                            last_sent_len["result_commentary"] = len(commentary)

                    # Before sending final object, ensure any corrected content from final JSON parsing
                    # is sent to the frontend (to fix escape sequence issues)
                    for field in ["initial_response", "generated_code"]:
                        current_content = field_content.get(field, "")
                        if current_content and last_sent_len[field] < len(current_content):
                            # Send any remaining content that wasn't streamed
                            delta = current_content[last_sent_len[field]:]
                            for i in range(0, len(delta), 8):
                                chunk = delta[i:i+8]
                                await ws.send_json({"event": "delta", "field": field, "delta": chunk})
                                await asyncio.sleep(0.02)
                            last_sent_len[field] = len(current_content)
                        elif current_content and len(current_content) == last_sent_len[field]:
                            # Force a replacement delta to ensure corrected escape sequences are sent
                            # This handles the case where string lengths match but content differs
                            await ws.send_json({"event": "replace", "field": field, "content": current_content})

                    # Send final assembled object
                    await ws.send_json({
                        "event": "end",
                        "final": field_content
                    })

                except Exception as e:
                    # Log the full error for debugging
                    logger.error(f"LM Studio processing error: {str(e)}", exc_info=True)
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

