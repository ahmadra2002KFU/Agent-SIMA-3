"""
Streaming Controller for AI Data Analysis Application

This module manages WebSocket streaming with atomic operations and graceful error handling.
Provides smooth real-time updates while ensuring data integrity.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class StreamingState:
    """State tracking for streaming operations."""
    field_positions: Dict[str, int]
    total_sent: int
    is_streaming: bool
    last_event: Optional[str]
    
    def __post_init__(self):
        if not self.field_positions:
            self.field_positions = {
                'initial_response': 0,
                'generated_code': 0,
                'result_commentary': 0
            }


class StreamingController:
    """
    Controls WebSocket streaming with atomic operations and error recovery.
    Ensures smooth real-time updates while maintaining data integrity.
    """
    
    def __init__(self):
        self.active_streams: Dict[str, StreamingState] = {}
        self.streaming_stats = {
            'total_streams': 0,
            'successful_streams': 0,
            'failed_streams': 0,
            'bytes_streamed': 0,
            'messages_sent': 0,
            'reconnections': 0
        }
    
    async def stream_response(
        self,
        websocket: WebSocket,
        stream_id: str,
        response_generator: AsyncGenerator[Dict[str, Any], None]
    ) -> bool:
        """
        Stream response to WebSocket with atomic operations.
        
        Args:
            websocket: WebSocket connection
            stream_id: Unique identifier for this stream
            response_generator: Generator yielding response data
            
        Returns:
            True if streaming successful, False otherwise
        """
        self.streaming_stats['total_streams'] += 1
        
        # Initialize streaming state
        state = StreamingState(
            field_positions={},
            total_sent=0,
            is_streaming=True,
            last_event=None
        )
        self.active_streams[stream_id] = state
        
        try:
            # Send stream start event
            await self._send_safe(websocket, {
                "event": "stream_start",
                "stream_id": stream_id
            })
            
            # Process response chunks
            async for chunk in response_generator:
                if not state.is_streaming:
                    break
                
                success = await self._process_chunk(websocket, state, chunk)
                if not success:
                    await self._handle_streaming_error(websocket, stream_id, "Chunk processing failed")
                    return False
            
            # Send stream completion
            await self._send_safe(websocket, {
                "event": "stream_complete",
                "stream_id": stream_id,
                "total_sent": state.total_sent
            })
            
            self.streaming_stats['successful_streams'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Streaming error for {stream_id}: {e}", exc_info=True)
            await self._handle_streaming_error(websocket, stream_id, str(e))
            return False
        
        finally:
            # Cleanup
            state.is_streaming = False
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    async def stream_field_incrementally(
        self,
        websocket: WebSocket,
        field_name: str,
        content: str,
        state: StreamingState,
        chunk_size: int = 8,
        delay: float = 0.02
    ) -> bool:
        """
        Stream field content incrementally with smooth updates.
        
        Args:
            websocket: WebSocket connection
            field_name: Name of the field being streamed
            content: Complete content to stream
            state: Current streaming state
            chunk_size: Size of each chunk
            delay: Delay between chunks
            
        Returns:
            True if streaming successful, False otherwise
        """
        try:
            current_pos = state.field_positions.get(field_name, 0)
            
            if len(content) > current_pos:
                # Stream new content
                new_content = content[current_pos:]
                
                for i in range(0, len(new_content), chunk_size):
                    if not state.is_streaming:
                        return False
                    
                    chunk = new_content[i:i + chunk_size]
                    
                    success = await self._send_safe(websocket, {
                        "event": "delta",
                        "field": field_name,
                        "delta": chunk,
                        "position": current_pos + i
                    })
                    
                    if not success:
                        return False
                    
                    state.total_sent += len(chunk)
                    self.streaming_stats['bytes_streamed'] += len(chunk.encode('utf-8'))
                    
                    # await asyncio.sleep(delay)
                
                # Update position
                state.field_positions[field_name] = len(content)
            
            return True
            
        except Exception as e:
            logger.error(f"Field streaming error for {field_name}: {e}", exc_info=True)
            return False
    
    async def _process_chunk(
        self,
        websocket: WebSocket,
        state: StreamingState,
        chunk: Dict[str, Any]
    ) -> bool:
        """
        Process individual response chunk.
        
        Args:
            websocket: WebSocket connection
            state: Current streaming state
            chunk: Response chunk to process
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            event = chunk.get("event")
            state.last_event = event
            
            if event == "field_complete":
                # Handle complete field content
                field = chunk.get("field")
                content = chunk.get("content", "")
                
                if field in state.field_positions:
                    return await self.stream_field_incrementally(
                        websocket, field, content, state
                    )
                else:
                    # Send complete field at once
                    return await self._send_safe(websocket, {
                        "event": "field_complete",
                        "field": field,
                        "content": content
                    })
            
            elif event == "response_complete":
                # Handle complete response
                response = chunk.get("response", {})
                execution_results = chunk.get("execution_results")
                
                return await self._send_safe(websocket, {
                    "event": "end",
                    "final": response,
                    "execution_results": execution_results
                })
            
            elif event == "error":
                # Handle error events
                return await self._send_safe(websocket, chunk)
            
            elif event == "warnings":
                # Handle warning events
                return await self._send_safe(websocket, chunk)
            
            else:
                # Handle unknown events
                logger.warning(f"Unknown chunk event: {event}")
                return await self._send_safe(websocket, chunk)
            
        except Exception as e:
            logger.error(f"Chunk processing error: {e}", exc_info=True)
            return False
    
    async def _send_safe(self, websocket: WebSocket, data: Dict[str, Any]) -> bool:
        """
        Safely send data to WebSocket with error handling.
        
        Args:
            websocket: WebSocket connection
            data: Data to send
            
        Returns:
            True if send successful, False otherwise
        """
        try:
            await websocket.send_json(data)
            self.streaming_stats['messages_sent'] += 1
            return True
            
        except Exception as e:
            logger.error(f"WebSocket send error: {e}", exc_info=True)
            return False
    
    async def _handle_streaming_error(
        self,
        websocket: WebSocket,
        stream_id: str,
        error_message: str
    ) -> None:
        """
        Handle streaming errors gracefully.
        
        Args:
            websocket: WebSocket connection
            stream_id: Stream identifier
            error_message: Error description
        """
        try:
            self.streaming_stats['failed_streams'] += 1
            
            # Mark stream as failed
            if stream_id in self.active_streams:
                self.active_streams[stream_id].is_streaming = False
            
            # Send error notification
            await self._send_safe(websocket, {
                "event": "stream_error",
                "stream_id": stream_id,
                "error": error_message,
                "timestamp": asyncio.get_event_loop().time()
            })
            
        except Exception as e:
            logger.error(f"Error handling failed: {e}", exc_info=True)
    
    async def stream_fallback_response(
        self,
        websocket: WebSocket,
        user_message: str,
        error_message: str = ""
    ) -> bool:
        """
        Stream fallback response when main processing fails.
        
        Args:
            websocket: WebSocket connection
            user_message: Original user message
            error_message: Error that caused fallback
            
        Returns:
            True if fallback streaming successful
        """
        try:
            fallback_response = {
                'initial_response': f"I received your message: '{user_message}'. {error_message}",
                'generated_code': (
                    "# Fallback response - System temporarily unavailable\n"
                    "# Please try again or check system status\n"
                    "print('System is in fallback mode')\n"
                ),
                'result_commentary': "This is a fallback response. The system encountered an issue and is operating in safe mode."
            }
            
            # Stream fallback content
            for field, content in fallback_response.items():
                success = await self._send_safe(websocket, {
                    "event": "delta",
                    "field": field,
                    "delta": content
                })
                if not success:
                    return False
                
                # await asyncio.sleep(0.1)  # Brief delay between fields
            
            # Send completion
            await self._send_safe(websocket, {
                "event": "end",
                "final": fallback_response,
                "fallback": True
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Fallback streaming error: {e}", exc_info=True)
            return False
    
    def stop_stream(self, stream_id: str) -> bool:
        """
        Stop active stream.
        
        Args:
            stream_id: Stream to stop
            
        Returns:
            True if stream was stopped
        """
        if stream_id in self.active_streams:
            self.active_streams[stream_id].is_streaming = False
            return True
        return False
    
    def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active stream."""
        if stream_id in self.active_streams:
            state = self.active_streams[stream_id]
            return {
                'is_streaming': state.is_streaming,
                'total_sent': state.total_sent,
                'last_event': state.last_event,
                'field_positions': state.field_positions.copy()
            }
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get streaming statistics."""
        return self.streaming_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset streaming statistics."""
        for key in self.streaming_stats:
            self.streaming_stats[key] = 0


# Global streaming controller instance
streaming_controller = StreamingController()
