import time
from enum import Enum
from typing import Callable, Any
from loguru import logger

class CircuitState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, reject all requests
    HALF_OPEN = "HALF_OPEN" # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
    
    def __call__(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._can_retry():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN. Service unavailable.")
            
            try:
                result = func(*args, **kwargs)
                
                # Success - reset if needed
                if self.state == CircuitState.HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= 3:
                        self._reset()
                        logger.info("Circuit breaker reset to CLOSED")
                
                return result
                
            except self.expected_exceptions as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")
    
    def _can_retry(self) -> bool:
        if not self.last_failure_time:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.recovery_timeout
    
    def _reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None