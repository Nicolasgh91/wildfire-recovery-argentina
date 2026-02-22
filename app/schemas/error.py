"""
Standardized error response schemas for ForestGuard API.

Provides consistent error response format across all endpoints.
Follows RFC 7807 (Problem Details) structure for API errors.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """
    Detail about a specific error field.

    Used for validation errors to indicate which field failed.
    """

    loc: List[str] = Field(
        ..., description="Location of the error (e.g., ['body', 'email'])"
    )
    msg: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Error type identifier")


class ErrorResponse(BaseModel):
    """
    Standard error response format (RFC 7807 inspired).

    All API errors should use this format for consistency.

    Attributes:
        error: Short error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Human-readable error description
        status_code: HTTP status code
        details: Optional list of specific error details
        request_id: X-Request-ID for tracing (if available)
        timestamp: When the error occurred
        path: API path that generated the error
    """

    error: str = Field(
        ...,
        description="Error code",
        examples=["VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        examples=["The requested resource was not found"],
    )
    status_code: int = Field(
        ..., description="HTTP status code", examples=[400, 401, 404, 422, 500]
    )
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information for validation errors"
    )
    request_id: Optional[str] = Field(
        None, description="Request ID for tracing and support"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    path: Optional[str] = Field(None, description="API path that generated the error")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "status_code": 422,
                "details": [
                    {
                        "loc": ["body", "email"],
                        "msg": "value is not a valid email address",
                        "type": "value_error.email",
                    }
                ],
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-02-08T14:30:00Z",
                "path": "/api/v1/auth/register",
            }
        }


class NotFoundError(ErrorResponse):
    """404 Not Found error response."""

    error: str = "NOT_FOUND"
    status_code: int = 404


class UnauthorizedError(ErrorResponse):
    """401 Unauthorized error response."""

    error: str = "UNAUTHORIZED"
    status_code: int = 401


class ForbiddenError(ErrorResponse):
    """403 Forbidden error response."""

    error: str = "FORBIDDEN"
    status_code: int = 403


class ValidationError(ErrorResponse):
    """422 Validation error response."""

    error: str = "VALIDATION_ERROR"
    status_code: int = 422


class RateLimitError(ErrorResponse):
    """429 Rate limit exceeded response."""

    error: str = "RATE_LIMIT_EXCEEDED"
    status_code: int = 429
    retry_after: Optional[int] = Field(
        None, description="Seconds until rate limit resets"
    )


class InternalError(ErrorResponse):
    """500 Internal server error response."""

    error: str = "INTERNAL_ERROR"
    status_code: int = 500


class ServiceUnavailableError(ErrorResponse):
    """503 Service unavailable error response."""

    error: str = "SERVICE_UNAVAILABLE"
    status_code: int = 503


# Common error responses for OpenAPI documentation
ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": UnauthorizedError, "description": "Unauthorized"},
    403: {"model": ForbiddenError, "description": "Forbidden"},
    404: {"model": NotFoundError, "description": "Not Found"},
    422: {"model": ValidationError, "description": "Validation Error"},
    429: {"model": RateLimitError, "description": "Rate Limit Exceeded"},
    500: {"model": InternalError, "description": "Internal Server Error"},
    503: {"model": ServiceUnavailableError, "description": "Service Unavailable"},
}
