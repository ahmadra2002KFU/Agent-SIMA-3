"""
Response Buffer Manager for AI Data Analysis Application

This module provides atomic response processing with validation and rollback capabilities.
Ensures responses are fully validated before streaming to prevent corruption.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from server.validation_engine import validation_engine, ValidationResult
from server.serialization_engine import serialization_engine

logger = logging.getLogger(__name__)


class ResponseState(Enum):
    """States of response processing."""
    INITIALIZING = "initializing"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    VALIDATED = "validated"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ResponseBuffer:
    """Buffer for collecting and validating LLM responses."""
    initial_response: str = ""
    generated_code: str = ""
    result_commentary: str = ""
    state: ResponseState = ResponseState.INITIALIZING
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_results: Optional[Dict[str, Any]] = None
    
    def is_complete(self) -> bool:
        """Check if all required fields have content."""
        return bool(
            self.initial_response.strip() and
            self.result_commentary.strip()
        )
    
    def has_code(self) -> bool:
        """Check if generated code is present."""
        return bool(self.generated_code.strip())
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            'initial_response': self.initial_response,
            'generated_code': self.generated_code,
            'result_commentary': self.result_commentary
        }


class ResponseManager:
    """
    Manages atomic response processing with validation and rollback capabilities.
    Ensures system reliability by validating all content before streaming.
    """
    
    def __init__(self):
        self.active_buffers: Dict[str, ResponseBuffer] = {}
        self.processing_stats = {
            'total_responses': 0,
            'successful_responses': 0,
            'failed_responses': 0,
            'rollbacks_performed': 0,
            'validations_passed': 0,
            'validations_failed': 0
        }
    
    async def process_llm_response(
        self,
        response_id: str,
        llm_response_generator: AsyncGenerator[Dict[str, str], None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process LLM response with atomic validation and streaming.
        
        Args:
            response_id: Unique identifier for this response
            llm_response_generator: Generator yielding LLM response chunks
            
        Yields:
            Validated response chunks for streaming
        """
        self.processing_stats['total_responses'] += 1
        buffer = ResponseBuffer()
        self.active_buffers[response_id] = buffer
        
        try:
            buffer.state = ResponseState.COLLECTING
            
            # Collect complete response from LLM
            async for chunk in llm_response_generator:
                field = chunk.get("field")
                content = chunk.get("content", "")
                
                if field == "initial_response":
                    buffer.initial_response = content
                elif field == "generated_code":
                    buffer.generated_code = content
                elif field == "result_commentary":
                    buffer.result_commentary = content
            
            # Validate complete response
            buffer.state = ResponseState.VALIDATING
            validation_success = await self._validate_response(buffer)
            
            if validation_success:
                buffer.state = ResponseState.VALIDATED
                self.processing_stats['validations_passed'] += 1
                
                # Stream validated response
                async for chunk in self._stream_validated_response(buffer):
                    yield chunk
                
                buffer.state = ResponseState.COMPLETED
                self.processing_stats['successful_responses'] += 1
                
            else:
                # Validation failed - attempt recovery or rollback
                buffer.state = ResponseState.FAILED
                self.processing_stats['validations_failed'] += 1
                
                recovery_success = await self._attempt_recovery(buffer)
                if recovery_success:
                    buffer.state = ResponseState.VALIDATED
                    async for chunk in self._stream_validated_response(buffer):
                        yield chunk
                    buffer.state = ResponseState.COMPLETED
                    self.processing_stats['successful_responses'] += 1
                else:
                    # Complete rollback
                    await self._rollback_response(buffer)
                    yield {
                        "event": "error",
                        "message": "Response validation failed",
                        "errors": buffer.errors,
                        "warnings": buffer.warnings
                    }
                    self.processing_stats['failed_responses'] += 1
        
        except Exception as e:
            logger.error(f"Response processing error: {e}", exc_info=True)
            buffer.state = ResponseState.FAILED
            buffer.errors.append(f"Processing error: {str(e)}")
            await self._rollback_response(buffer)
            yield {
                "event": "error",
                "message": "Response processing failed",
                "error": str(e)
            }
            self.processing_stats['failed_responses'] += 1
        
        finally:
            # Cleanup
            if response_id in self.active_buffers:
                del self.active_buffers[response_id]
    
    async def _validate_response(self, buffer: ResponseBuffer) -> bool:
        """
        Validate complete response buffer.
        
        Args:
            buffer: Response buffer to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            # Validate structured response
            response_dict = buffer.to_dict()
            overall_result = validation_engine.validate_structured_response(response_dict)
            
            buffer.validation_results['overall'] = overall_result
            buffer.errors.extend(overall_result.errors)
            buffer.warnings.extend(overall_result.warnings)
            
            # Validate individual fields
            if buffer.initial_response.strip():
                initial_result = ValidationResult(True, [], [])  # Basic text validation
                buffer.validation_results['initial_response'] = initial_result
            
            if buffer.has_code():
                code_result = validation_engine.validate_python_code(buffer.generated_code)
                buffer.validation_results['generated_code'] = code_result
                
                if code_result.is_valid and code_result.cleaned_content:
                    buffer.generated_code = code_result.cleaned_content
                
                buffer.errors.extend(code_result.errors)
                buffer.warnings.extend(code_result.warnings)
            
            if buffer.result_commentary.strip():
                commentary_result = ValidationResult(True, [], [])  # Basic text validation
                buffer.validation_results['result_commentary'] = commentary_result
            
            # Overall validation passes if no critical errors
            return len(buffer.errors) == 0
            
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            buffer.errors.append(f"Validation error: {str(e)}")
            return False
    
    async def _attempt_recovery(self, buffer: ResponseBuffer) -> bool:
        """
        Attempt to recover from validation failures.
        
        Args:
            buffer: Failed response buffer
            
        Returns:
            True if recovery successful, False otherwise
        """
        try:
            recovery_attempts = 0
            max_attempts = 3
            
            while recovery_attempts < max_attempts:
                recovery_attempts += 1
                
                # Try to fix code issues
                if buffer.has_code() and 'generated_code' in buffer.validation_results:
                    code_result = buffer.validation_results['generated_code']
                    if not code_result.is_valid and code_result.cleaned_content:
                        buffer.generated_code = code_result.cleaned_content
                        buffer.warnings.append(f"Applied code recovery attempt {recovery_attempts}")
                        
                        # Re-validate
                        new_code_result = validation_engine.validate_python_code(buffer.generated_code)
                        if new_code_result.is_valid:
                            buffer.validation_results['generated_code'] = new_code_result
                            buffer.errors = [e for e in buffer.errors if 'Code validation:' not in e]
                            
                            # Check if overall validation now passes
                            if len([e for e in buffer.errors if 'Code validation:' not in e]) == 0:
                                return True
                
                await asyncio.sleep(0.1)  # Brief pause between attempts
            
            return False
            
        except Exception as e:
            logger.error(f"Recovery attempt error: {e}", exc_info=True)
            return False
    
    async def _rollback_response(self, buffer: ResponseBuffer) -> None:
        """
        Rollback failed response.
        
        Args:
            buffer: Response buffer to rollback
        """
        try:
            buffer.state = ResponseState.ROLLED_BACK
            self.processing_stats['rollbacks_performed'] += 1
            
            # Clear potentially corrupted content
            buffer.initial_response = ""
            buffer.generated_code = ""
            buffer.result_commentary = ""
            
            logger.warning(f"Response rolled back due to validation failures: {buffer.errors}")
            
        except Exception as e:
            logger.error(f"Rollback error: {e}", exc_info=True)
    
    async def _stream_validated_response(self, buffer: ResponseBuffer) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream validated response content.
        
        Args:
            buffer: Validated response buffer
            
        Yields:
            Response chunks for streaming
        """
        try:
            buffer.state = ResponseState.STREAMING
            
            # Stream initial response
            if buffer.initial_response:
                yield {
                    "event": "field_complete",
                    "field": "initial_response",
                    "content": buffer.initial_response
                }
            
            # Stream generated code
            if buffer.generated_code:
                yield {
                    "event": "field_complete",
                    "field": "generated_code",
                    "content": buffer.generated_code
                }
            
            # Stream result commentary
            if buffer.result_commentary:
                yield {
                    "event": "field_complete",
                    "field": "result_commentary",
                    "content": buffer.result_commentary
                }
            
            # Include validation warnings if any
            if buffer.warnings:
                yield {
                    "event": "warnings",
                    "warnings": buffer.warnings
                }
            
            # Final response
            yield {
                "event": "response_complete",
                "response": buffer.to_dict(),
                "execution_results": buffer.execution_results
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {
                "event": "error",
                "message": "Streaming failed",
                "error": str(e)
            }
    
    def get_buffer_status(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active response buffer."""
        if response_id in self.active_buffers:
            buffer = self.active_buffers[response_id]
            return {
                'state': buffer.state.value,
                'is_complete': buffer.is_complete(),
                'has_code': buffer.has_code(),
                'errors': buffer.errors,
                'warnings': buffer.warnings
            }
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        for key in self.processing_stats:
            self.processing_stats[key] = 0


# Global response manager instance
response_manager = ResponseManager()
