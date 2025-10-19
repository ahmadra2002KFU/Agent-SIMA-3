"""
LM Studio API client for streaming responses.
"""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
import aiohttp
import logging
import re
# Temporarily comment out new architecture imports for testing
# from server.validation_engine import validation_engine
# from server.error_handler import error_handler

logger = logging.getLogger(__name__)


class LMStudioClient:
    """Client for communicating with Groq API (Kimi K2 model)."""

    def __init__(self, base_url: str = "https://api.groq.com/openai", model: str = "moonshotai/kimi-k2-instruct-0905", api_key: str = "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"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized Groq API client with base_url={self.base_url}, model={self.model}")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def check_health(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            session = await self._get_session()
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            async with session.get(f"{self.base_url}/v1/models", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                is_healthy = response.status == 200
                if is_healthy:
                    logger.info("Groq API health check passed")
                else:
                    logger.warning(f"Groq API health check failed with status {response.status}")
                return is_healthy
        except Exception as e:
            logger.warning(f"Groq API health check failed: {e}")
            return False
    
    async def stream_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion from LM Studio.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Yields:
            str: Token chunks from the model
        """
        try:
            session = await self._get_session()
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **kwargs
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f"Sending request to Groq API: {self.base_url}/v1/chat/completions")

            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Groq API error {response.status}: {error_text}")
                    raise Exception(f"Groq API error {response.status}: {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line:
                        continue
                    
                    if line.startswith("data: "):
                        line = line[6:]  # Remove "data: " prefix
                    
                    if line == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(line)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        # Skip malformed JSON lines
                        continue
                        
        except Exception as e:
            logger.error(f"Error streaming from Groq API: {e}")
            # Yield error message as fallback
            yield f"Error: {str(e)}"
    
    async def generate_structured_response(
        self,
        user_message: str,
        system_prompt: str,
        user_rules: list[str] = None,
        file_metadata: Dict[str, Any] = None,
        conversation_history: list[Dict[str, str]] = None,
        available_tools: list[str] = None,
        code_execution_results: Dict[str, Any] = None,
        initial_response_temp: float = 0.7,
        generated_code_temp: float = 0.3,
        result_commentary_temp: float = 0.2
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        Generate a structured response with the three required fields using different temperatures.

        Args:
            user_message: The user's current message
            system_prompt: System prompt for the LLM
            user_rules: List of user-defined rules
            file_metadata: Metadata about uploaded files
            conversation_history: Previous conversation messages
            available_tools: List of available tools/functions
            code_execution_results: Results from previous code execution
            initial_response_temp: Temperature for initial response (default: 0.7)
            generated_code_temp: Temperature for code generation (default: 0.3)
            result_commentary_temp: Temperature for result commentary (default: 0.2)

        Yields:
            Dict with 'field' and 'content' keys for streaming updates
        """
        # Build the complete context
        messages = []

        # Build file context if available
        file_context = ""
        if file_metadata:
            basic_info = file_metadata.get('basic_info', {})
            columns = file_metadata.get('columns', {})
            data_quality = file_metadata.get('data_quality', {})

            file_context = f"""
CURRENT UPLOADED FILE (Available as 'df' variable):
- Filename: {basic_info.get('filename', 'Unknown')}
- Shape: {basic_info.get('shape', {}).get('rows', 0)} rows × {basic_info.get('shape', {}).get('columns', 0)} columns
- Columns: {', '.join(basic_info.get('column_names', []))}
- Data Quality Score: {data_quality.get('data_quality_score', 'Unknown')}/100

IMPORTANT: The uploaded data is already loaded as a pandas DataFrame called 'df'.
DO NOT use pd.read_csv() - use 'df' directly in your code.

COLUMN DETAILS:
"""
            for col_name, col_info in columns.items():
                file_context += f"- {col_name}: {col_info.get('column_type', 'unknown')} type, {col_info.get('non_null_count', 0)} non-null values"
                if col_info.get('column_type') == 'numeric':
                    file_context += f", range: {col_info.get('min', 'N/A')}-{col_info.get('max', 'N/A')}, mean: {col_info.get('mean', 'N/A')}"
                elif col_info.get('column_type') == 'categorical':
                    top_values = col_info.get('top_values', [])
                    if top_values:
                        file_context += f", most common: {top_values[0].get('value', 'N/A')}"
                file_context += "\n"

        # Build code execution context if available
        execution_context = ""
        if code_execution_results:
            executed_code = code_execution_results.get('executed_code', 'No code available')
            execution_context = f"""
PREVIOUS CODE EXECUTION CONTEXT:
- Status: {'Success' if code_execution_results.get('success', False) else 'Failed'}
- Executed Code:
```python
{executed_code}
```
- Console Output: {code_execution_results.get('output', 'No output')}
- Captured Results: {json.dumps(code_execution_results.get('results', {}), indent=2) if code_execution_results.get('results') else 'No results'}

Use this complete execution context (code + results) to provide meaningful commentary and insights.
"""

        # System message with structured response instructions
        system_content = f"""{system_prompt}

{file_context}

{execution_context}

You must respond in a structured JSON format with exactly three fields:
1. "initial_response": Your initial analysis/understanding of the request
2. "generated_code": Python code to execute (if applicable, otherwise empty string) - MUST assign final output to 'result', 'output', 'fig', or 'figure' variable
3. "result_commentary": CONCISE, FACTUAL interpretation of results

CRITICAL GUIDELINES FOR generated_code:
- ALWAYS assign your final output to a variable named 'result' or 'output'
- For visualizations, assign to 'fig' or 'figure'
- Without this assignment, results won't be captured!

CRITICAL GUIDELINES FOR result_commentary:
- Start with the direct answer to the user's question
- State exact numbers and percentages found
- Explain the methodology used by referencing the executed code (e.g., "The code filtered the Nationality column using df['Nationality'].str.contains('Saudi')")
- Mention specific pandas operations, functions, or techniques used
- Keep additional insights brief and relevant
- Avoid speculation, verbose analysis, or tangential observations
- Focus on what the data actually shows and how the code achieved those results

EXAMPLE for "How many Saudi patients are there?":
"The analysis found 12 Saudi patients out of 20 total patients (60%). The code filtered the Nationality column using df['Nationality'].str.contains('Saudi', case=False, na=False) to identify all patients with Saudi nationality. The dataset shows patients from 8 different nationalities, with Saudi Arabia being the most common."

User Rules: {user_rules or []}
Available Tools: {available_tools or []}

When a file is uploaded, use the file metadata provided above to give specific insights about the actual data.
If code execution results are provided, focus on interpreting those results in your commentary.
Respond ONLY with valid JSON in the exact format specified."""
        
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Use lower temperature for more precise, factual responses
        # The result_commentary field benefits from lower temperature to reduce hallucination
        temperature = result_commentary_temp  # Use the lowest temperature for overall precision

        # Stream the response and parse it incrementally for faster UX
        full_response = ""
        # Track partial content extracted per field to emit only new data
        partial_buffers: Dict[str, str] = {
            "initial_response": "",
            "generated_code": "",
            "result_commentary": "",
        }

        def extract_partial(json_text: str, field: str) -> Optional[str]:
            """Best-effort extraction of the (possibly partial) string value of a top-level JSON field.
            Assumes the model is emitting a JSON object with string fields. Handles escaped quotes and
            properly decodes JSON escape sequences like \\n, \\t, \\", etc. Returns the string content
            without surrounding quotes if the field has started; returns None if the field key hasn't
            appeared yet.
            """
            try:
                key = f'"{field}"'
                key_idx = json_text.find(key)
                if key_idx == -1:
                    return None

                # Find the colon after the key
                colon_idx = json_text.find(":", key_idx)
                if colon_idx == -1:
                    return None

                # Find the opening quote for the string value
                i = colon_idx + 1
                # Skip whitespace
                while i < len(json_text) and json_text[i] in " \t\r\n":
                    i += 1
                if i >= len(json_text) or json_text[i] != '"':
                    return None

                # Move past opening quote
                i += 1
                # Scan until we hit an unescaped closing quote or run out of text (partial)
                # Keep escape sequences intact for proper JSON decoding
                escaped = False
                raw_chars = []
                string_complete = False

                while i < len(json_text):
                    ch = json_text[i]
                    raw_chars.append(ch)

                    if escaped:
                        escaped = False
                    else:
                        if ch == "\\":
                            escaped = True
                        elif ch == '"':
                            # End of the string value
                            string_complete = True
                            raw_chars.pop()  # Remove the closing quote
                            break
                    i += 1

                raw_content = "".join(raw_chars)

                # If the string is complete, use JSON decoder for proper escape sequence handling
                if string_complete:
                    try:
                        # Use json.loads to properly decode all escape sequences
                        decoded = json.loads(f'"{raw_content}"')
                        return decoded
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error for complete string in field '{field}': {e}")
                        # If JSON decoding fails, return raw content but clean it up
                        return raw_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
                else:
                    # For partial strings, try to decode what we have, but fall back to raw if it fails
                    try:
                        # Try to decode the partial content
                        decoded = json.loads(f'"{raw_content}"')
                        return decoded
                    except json.JSONDecodeError:
                        # For partial strings that can't be decoded, return as-is
                        # But do basic cleanup of common escape sequences
                        cleaned = raw_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
                        return cleaned

            except Exception as e:
                logger.error(f"Error in extract_partial for field '{field}': {e}")
                return None

        async for chunk in self.stream_completion(messages, temperature=temperature):
            full_response += chunk

            # Try to incrementally extract and stream each field's partial content as the stream progresses
            for fld in ["initial_response", "generated_code", "result_commentary"]:
                try:
                    partial = extract_partial(full_response, fld)
                    if partial is None:
                        continue
                    prev = partial_buffers[fld]
                    if len(partial) > len(prev):
                        # Emit only the newly added portion
                        delta = partial[len(prev):]
                        partial_buffers[fld] = partial
                        # Yield the cumulative content so far (server will compute delta)
                        yield {"field": fld, "content": partial}
                except Exception:
                    # Best-effort; ignore parser errors and continue accumulating
                    continue

        # Once streaming is complete, attempt a final JSON extraction
        try:
            full_response = full_response.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(full_response.strip())
            for field in ["initial_response", "generated_code", "result_commentary"]:
                if field in parsed:
                    # Ensure final content is yielded at least once
                    yield {"field": field, "content": parsed[field]}
        except json.JSONDecodeError:
            pass

        # If nothing was produced at all
        if not full_response.strip() and all(len(v) == 0 for v in partial_buffers.values()):
            yield {"field": "initial_response", "content": "No response received from Groq API"}
            yield {"field": "generated_code", "content": ""}
            yield {"field": "result_commentary", "content": "Unable to process request"}


# Global client instance
lm_client = LMStudioClient()
