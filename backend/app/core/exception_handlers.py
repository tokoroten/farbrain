"""Exception handlers for converting custom exceptions to HTTP responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from backend.app.core.exceptions import (
    FarBrainException,
    SessionNotFoundError,
    SessionNotAcceptingIdeasError,
    SessionEndedError,
    UserNotFoundError,
    IdeaNotFoundError,
    ClusterNotFoundError,
    LLMServiceError,
    EmbeddingServiceError,
    ClusteringServiceError,
)


async def farbrain_exception_handler(request: Request, exc: FarBrainException) -> JSONResponse:
    """
    Handle all FarBrain custom exceptions and convert to appropriate HTTP responses.

    Args:
        request: The incoming request
        exc: The exception that was raised

    Returns:
        JSONResponse with appropriate status code and error details
    """
    # Map exception types to HTTP status codes
    if isinstance(exc, (SessionNotFoundError, UserNotFoundError, IdeaNotFoundError, ClusterNotFoundError)):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, (SessionNotAcceptingIdeasError, SessionEndedError)):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, (LLMServiceError, EmbeddingServiceError, ClusteringServiceError)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        # Generic FarBrainException
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": exc.message,
            "type": exc.__class__.__name__,
            **({"info": exc.details} if exc.details else {})
        }
    )


def register_exception_handlers(app):
    """
    Register all custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(FarBrainException, farbrain_exception_handler)
