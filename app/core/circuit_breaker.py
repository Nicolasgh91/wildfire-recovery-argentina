"""
=============================================================================
CIRCUIT BREAKER PATTERN FOR EXTERNAL SERVICES
=============================================================================

Implements the Circuit Breaker pattern to handle failures in external 
services gracefully. Prevents cascading failures and provides fallback
behavior when services are unavailable.

States:
    CLOSED: Normal operation, requests pass through
    OPEN: Service is down, fail fast without making requests
    HALF_OPEN: Testing if service has recovered

Usage:
    from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerError
    
    cb = CircuitBreaker(name="gee", failure_threshold=5, recovery_timeout=60)
    
    try:
        result = cb.call(gee_service.get_image, fire_id)
    except CircuitBreakerError:
        # Fallback logic
        result = get_cached_image(fire_id)

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-02-08
=============================================================================
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from app.core.alerts import send_alert
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Requests rejected due to open circuit
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    def __init__(
        self, message: str, circuit_name: str, retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Circuit Breaker implementation for protecting external service calls.

    Thread-safe implementation that can be shared across multiple requests.

    Attributes:
        name: Identifier for this circuit (e.g., "gee", "redis")
        failure_threshold: Number of consecutive failures to open circuit
        success_threshold: Number of consecutive successes in half-open to close
        recovery_timeout: Seconds to wait before testing recovery
        stats: Current circuit statistics
    """

    # Registry of all circuit breakers for monitoring
    _registry: Dict[str, "CircuitBreaker"] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        recovery_timeout: int = 60,
        excluded_exceptions: Optional[tuple] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit
            failure_threshold: Consecutive failures to open circuit (default: 5)
            success_threshold: Consecutive successes to close from half-open (default: 2)
            recovery_timeout: Seconds to wait in open state before half-open (default: 60)
            excluded_exceptions: Exceptions that should NOT count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout
        self.excluded_exceptions = excluded_exceptions or ()

        self._state = CircuitState.CLOSED
        self._state_lock = threading.RLock()
        self._last_state_change = datetime.utcnow()
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._stats = CircuitStats()

        # Register this circuit breaker
        with CircuitBreaker._lock:
            CircuitBreaker._registry[name] = self

        logger.info(
            f"Circuit breaker '{name}' initialized (threshold={failure_threshold}, timeout={recovery_timeout}s)"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, with automatic half-open transition."""
        with self._state_lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                elapsed = (datetime.utcnow() - self._last_state_change).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get current circuit statistics."""
        with self._state_lock:
            self._stats.current_state = self._state
            self._stats.consecutive_failures = self._consecutive_failures
            self._stats.consecutive_successes = self._consecutive_successes
            return self._stats

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state with logging."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.utcnow()
        self._stats.state_changes += 1

        if new_state == CircuitState.HALF_OPEN:
            self._consecutive_successes = 0
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0

        logger.warning(
            f"Circuit breaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}"
        )
        if new_state == CircuitState.OPEN:
            send_alert(
                subject=f"Circuit breaker OPEN: {self.name}",
                body=(
                    f"Circuit '{self.name}' transitioned to OPEN at {self._last_state_change.isoformat()}.\n"
                    f"Failures: {self._consecutive_failures} / Threshold: {self.failure_threshold}\n"
                    f"Recovery timeout: {self.recovery_timeout}s"
                ),
            )

    def _record_success(self) -> None:
        """Record a successful call."""
        with self._state_lock:
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.last_success_time = datetime.utcnow()
            self._consecutive_failures = 0
            self._consecutive_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                if self._consecutive_successes >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        with self._state_lock:
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            self._stats.last_failure_time = datetime.utcnow()
            self._consecutive_successes = 0
            self._consecutive_failures += 1

            logger.warning(
                f"Circuit breaker '{self.name}' failure #{self._consecutive_failures}: {type(exception).__name__}"
            )

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._consecutive_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: The function to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            The return value of the function

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from the wrapped function
        """
        current_state = self.state  # This may trigger half-open transition

        if current_state == CircuitState.OPEN:
            self._stats.rejected_requests += 1
            retry_after = self.recovery_timeout - int(
                (datetime.utcnow() - self._last_state_change).total_seconds()
            )
            raise CircuitBreakerError(
                f"Circuit '{self.name}' is OPEN. Service unavailable.",
                circuit_name=self.name,
                retry_after=max(0, retry_after),
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            # Check if this exception should be excluded (e.g., validation errors)
            if isinstance(e, self.excluded_exceptions):
                self._record_success()  # Don't count as failure
                raise

            self._record_failure(e)
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function through the circuit breaker.

        Same as call() but for async functions.
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            self._stats.rejected_requests += 1
            retry_after = self.recovery_timeout - int(
                (datetime.utcnow() - self._last_state_change).total_seconds()
            )
            raise CircuitBreakerError(
                f"Circuit '{self.name}' is OPEN. Service unavailable.",
                circuit_name=self.name,
                retry_after=max(0, retry_after),
            )

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            if isinstance(e, self.excluded_exceptions):
                self._record_success()
                raise

            self._record_failure(e)
            raise

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        with self._state_lock:
            self._transition_to(CircuitState.CLOSED)
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset")

    @classmethod
    def get_all_stats(cls) -> Dict[str, CircuitStats]:
        """Get stats for all registered circuit breakers."""
        with cls._lock:
            return {name: cb.stats for name, cb in cls._registry.items()}

    @classmethod
    def get_circuit(cls, name: str) -> Optional["CircuitBreaker"]:
        """Get a specific circuit breaker by name."""
        with cls._lock:
            return cls._registry.get(name)


# =============================================================================
# DECORATOR VERSION
# =============================================================================


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    recovery_timeout: int = 60,
    fallback: Optional[Callable] = None,
):
    """
    Decorator to apply circuit breaker to a function.

    Args:
        name: Circuit breaker name
        failure_threshold: Consecutive failures to open
        success_threshold: Consecutive successes to close from half-open
        recovery_timeout: Seconds before testing recovery
        fallback: Optional fallback function when circuit is open

    Example:
        @circuit_breaker("gee", fallback=get_cached_image)
        def get_satellite_image(fire_id: str):
            return gee_service.get_image(fire_id)
    """
    cb = CircuitBreaker.get_circuit(name)
    if cb is None:
        cb = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            recovery_timeout=recovery_timeout,
        )

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return cb.call(func, *args, **kwargs)
            except CircuitBreakerError:
                if fallback:
                    logger.info(
                        f"Circuit '{name}' open, using fallback for {func.__name__}"
                    )
                    return fallback(*args, **kwargs)
                raise

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# =============================================================================
# GEE-SPECIFIC CIRCUIT BREAKER
# =============================================================================

# Pre-configured circuit breaker for Google Earth Engine
gee_circuit = CircuitBreaker(
    name="gee",
    failure_threshold=5,  # Open after 5 consecutive failures (RES-001)
    success_threshold=1,  # Close after 1 successful probe in HALF_OPEN
    recovery_timeout=60,  # Wait 60s before testing recovery
    excluded_exceptions=(  # These shouldn't trigger the breaker
        ValueError,  # Validation errors (user input)
        KeyError,  # Missing data (not service failure)
    ),
)


def with_gee_circuit(func: Callable) -> Callable:
    """
    Decorator to wrap a function with the GEE circuit breaker.

    Example:
        @with_gee_circuit
        def get_fire_imagery(fire_id: str):
            return gee_service.get_best_image(fire_id)
    """

    def wrapper(*args, **kwargs):
        return gee_circuit.call(func, *args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
