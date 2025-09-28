"""
Error Handler for AI Data Analysis Application

This module provides comprehensive error handling with circuit breaker patterns
and graceful degradation to prevent cascading failures.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class ComponentState(Enum):
    """States for system components."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    CIRCUIT_OPEN = "circuit_open"
    RECOVERING = "recovering"


@dataclass
class ErrorStats:
    """Error statistics for a component."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: Optional[float] = None
    consecutive_failures: int = 0
    circuit_open_time: Optional[float] = None
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return 1.0 - self.failure_rate


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Consecutive failures to open circuit
    failure_rate_threshold: float = 0.5  # Failure rate to open circuit
    timeout: float = 60.0  # Seconds to keep circuit open
    recovery_timeout: float = 30.0  # Seconds for recovery attempts
    max_requests_half_open: int = 3  # Max requests during recovery


class ComponentCircuitBreaker:
    """Circuit breaker for individual components."""
    
    def __init__(self, component_name: str, config: CircuitBreakerConfig):
        self.component_name = component_name
        self.config = config
        self.state = ComponentState.HEALTHY
        self.stats = ErrorStats()
        self.half_open_requests = 0
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == ComponentState.CIRCUIT_OPEN:
            if self._should_attempt_reset():
                self.state = ComponentState.RECOVERING
                self.half_open_requests = 0
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker open for {self.component_name}")
        
        if self.state == ComponentState.RECOVERING:
            if self.half_open_requests >= self.config.max_requests_half_open:
                raise CircuitBreakerOpenError(f"Circuit breaker in recovery for {self.component_name}")
            self.half_open_requests += 1
        
        self.stats.total_requests += 1
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_success(self) -> None:
        """Record successful operation."""
        self.stats.successful_requests += 1
        self.stats.consecutive_failures = 0
        
        if self.state == ComponentState.RECOVERING:
            if self.half_open_requests >= self.config.max_requests_half_open:
                self.state = ComponentState.HEALTHY
                logger.info(f"Circuit breaker closed for {self.component_name}")
        elif self.state in [ComponentState.DEGRADED, ComponentState.FAILING]:
            self.state = ComponentState.HEALTHY
    
    def _record_failure(self) -> None:
        """Record failed operation."""
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.last_failure_time = time.time()
        
        # Check if circuit should open
        if (self.stats.consecutive_failures >= self.config.failure_threshold or
            self.stats.failure_rate >= self.config.failure_rate_threshold):
            
            self.state = ComponentState.CIRCUIT_OPEN
            self.stats.circuit_open_time = time.time()
            logger.warning(f"Circuit breaker opened for {self.component_name}")
        
        elif self.stats.consecutive_failures >= 2:
            self.state = ComponentState.DEGRADED
        elif self.stats.consecutive_failures >= 1:
            self.state = ComponentState.FAILING
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if self.stats.circuit_open_time is None:
            return False
        
        return time.time() - self.stats.circuit_open_time >= self.config.timeout
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            'component': self.component_name,
            'state': self.state.value,
            'stats': {
                'total_requests': self.stats.total_requests,
                'successful_requests': self.stats.successful_requests,
                'failed_requests': self.stats.failed_requests,
                'failure_rate': self.stats.failure_rate,
                'success_rate': self.stats.success_rate,
                'consecutive_failures': self.stats.consecutive_failures
            },
            'circuit_open_time': self.stats.circuit_open_time,
            'last_failure_time': self.stats.last_failure_time
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class ErrorHandler:
    """
    Comprehensive error handler with circuit breaker patterns and graceful degradation.
    Prevents cascading failures and provides system resilience.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, ComponentCircuitBreaker] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # Initialize circuit breakers for key components
        self._initialize_circuit_breakers()
    
    def _initialize_circuit_breakers(self) -> None:
        """Initialize circuit breakers for system components."""
        components = {
            'lm_studio': CircuitBreakerConfig(failure_threshold=3, timeout=30.0),
            'code_executor': CircuitBreakerConfig(failure_threshold=5, timeout=60.0),
            'serialization': CircuitBreakerConfig(failure_threshold=10, timeout=30.0),
            'validation': CircuitBreakerConfig(failure_threshold=10, timeout=30.0),
            'file_handler': CircuitBreakerConfig(failure_threshold=5, timeout=60.0),
        }
        
        for component, config in components.items():
            self.circuit_breakers[component] = ComponentCircuitBreaker(component, config)
    
    async def execute_with_circuit_breaker(
        self,
        component_name: str,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            component_name: Name of the component
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
        """
        if component_name not in self.circuit_breakers:
            # Create default circuit breaker for unknown components
            self.circuit_breakers[component_name] = ComponentCircuitBreaker(
                component_name, CircuitBreakerConfig()
            )
        
        circuit_breaker = self.circuit_breakers[component_name]
        return await circuit_breaker.call(func, *args, **kwargs)
    
    def circuit_breaker(self, component_name: str):
        """Decorator for circuit breaker protection."""
        def decorator(func: Callable[..., Awaitable[Any]]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self.execute_with_circuit_breaker(
                    component_name, func, *args, **kwargs
                )
            return wrapper
        return decorator
    
    def record_error(
        self,
        component: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record error for analysis and monitoring.
        
        Args:
            component: Component where error occurred
            error: The exception that occurred
            context: Additional context information
        """
        error_record = {
            'timestamp': time.time(),
            'component': component,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.error_history.append(error_record)
        
        # Maintain history size
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        logger.error(f"Error in {component}: {error}", exc_info=True)
    
    def get_component_health(self, component_name: str) -> Dict[str, Any]:
        """Get health status of a component."""
        if component_name in self.circuit_breakers:
            return self.circuit_breakers[component_name].get_status()
        
        return {
            'component': component_name,
            'state': 'unknown',
            'stats': {},
            'message': 'Component not monitored'
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        component_statuses = {}
        overall_health = ComponentState.HEALTHY
        
        for component_name, circuit_breaker in self.circuit_breakers.items():
            status = circuit_breaker.get_status()
            component_statuses[component_name] = status
            
            # Determine overall health
            component_state = ComponentState(status['state'])
            if component_state == ComponentState.CIRCUIT_OPEN:
                overall_health = ComponentState.CIRCUIT_OPEN
            elif component_state == ComponentState.FAILING and overall_health == ComponentState.HEALTHY:
                overall_health = ComponentState.DEGRADED
        
        # Recent error analysis
        recent_errors = [
            error for error in self.error_history
            if time.time() - error['timestamp'] < 300  # Last 5 minutes
        ]
        
        return {
            'overall_health': overall_health.value,
            'components': component_statuses,
            'recent_errors': len(recent_errors),
            'total_errors': len(self.error_history),
            'timestamp': time.time()
        }
    
    def reset_circuit_breaker(self, component_name: str) -> bool:
        """Manually reset a circuit breaker."""
        if component_name in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[component_name]
            circuit_breaker.state = ComponentState.HEALTHY
            circuit_breaker.stats.consecutive_failures = 0
            circuit_breaker.stats.circuit_open_time = None
            logger.info(f"Circuit breaker manually reset for {component_name}")
            return True
        return False
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [
            error for error in self.error_history
            if error['timestamp'] >= cutoff_time
        ]
        
        # Group by component
        component_errors = {}
        error_types = {}
        
        for error in recent_errors:
            component = error['component']
            error_type = error['error_type']
            
            component_errors[component] = component_errors.get(component, 0) + 1
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'time_period_hours': hours,
            'total_errors': len(recent_errors),
            'errors_by_component': component_errors,
            'errors_by_type': error_types,
            'most_problematic_component': max(component_errors.items(), key=lambda x: x[1])[0] if component_errors else None
        }


# Global error handler instance
error_handler = ErrorHandler()
