"""
LM Studio API client for streaming responses.
"""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)


class LMStudioClient:
    """Client for communicating with LM Studio API."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:1234", model: str = "local-model"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.session: Optional[aiohttp.ClientSession] = None
    
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
        """Check if LM Studio is running and accessible."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/v1/models", timeout=5) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {e}")
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
            
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LM Studio API error {response.status}: {error_text}")
                
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
            logger.error(f"Error streaming from LM Studio: {e}")
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
            execution_context = f"""
PREVIOUS CODE EXECUTION RESULTS:
- Status: {'Success' if code_execution_results.get('success', False) else 'Failed'}
- Output: {code_execution_results.get('output', 'No output')}
- Results: {json.dumps(code_execution_results.get('results', {}), indent=2) if code_execution_results.get('results') else 'No results'}

Use these results to provide meaningful commentary and insights.
"""

        # System message with structured response instructions
        system_content = f"""{system_prompt}

{file_context}

{execution_context}

You must respond in a structured JSON format with exactly three fields:
1. "initial_response": Your initial analysis/understanding of the request
2. "generated_code": Python code to execute (if applicable, otherwise empty string)
3. "result_commentary": CONCISE, FACTUAL interpretation of results

CRITICAL GUIDELINES FOR result_commentary:
- Start with the direct answer to the user's question
- State exact numbers and percentages found
- Mention the method used (e.g., "filtered Nationality column for 'Saudi'")
- Keep additional insights brief and relevant
- Avoid speculation, verbose analysis, or tangential observations
- Focus on what the data actually shows, not what it might mean

EXAMPLE for "How many Saudi patients are there?":
"The analysis found 12 Saudi patients out of 20 total patients (60%), based on filtering the Nationality column for entries containing 'Saudi'. The dataset shows patients from 8 different nationalities, with Saudi Arabia being the most common."

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

        # Stream the response and parse it
        full_response = ""
        async for chunk in self.stream_completion(messages, temperature=temperature):
            full_response += chunk

            # Try to parse partial JSON to extract fields
            try:
                # Look for complete JSON structure
                if full_response.strip().endswith("}"):
                    parsed = json.loads(full_response.strip())

                    # Yield each field if it exists
                    for field in ["initial_response", "generated_code", "result_commentary"]:
                        if field in parsed:
                            yield {"field": field, "content": parsed[field]}
                    break

            except json.JSONDecodeError:
                # Continue accumulating until we have valid JSON
                continue
        
        # Fallback if JSON parsing fails
        if not full_response.strip():
            yield {"field": "initial_response", "content": "No response received from LM Studio"}
            yield {"field": "generated_code", "content": ""}
            yield {"field": "result_commentary", "content": "Unable to process request"}


# Global client instance
lm_client = LMStudioClient()
