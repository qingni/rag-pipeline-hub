"""Error handling utilities."""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any


class AppException(Exception):
    """Base application exception."""
    
    def __init__(self, code: str, message: str, details: Dict[str, Any] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("VALIDATION_ERROR", message, details)


class NotFoundError(AppException):
    """Resource not found error."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            "NOT_FOUND",
            f"{resource} not found: {identifier}",
            {"resource": resource, "identifier": identifier}
        )


class ProcessingError(AppException):
    """Processing operation error."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("PROCESSING_ERROR", message, details)


class StorageError(AppException):
    """Storage operation error."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__("STORAGE_ERROR", message, details)


def create_error_response(error: AppException, status_code: int = 400) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        error: Application exception
        status_code: HTTP status code
        
    Returns:
        JSON response
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details
            }
        }
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for AppException."""
    status_map = {
        "VALIDATION_ERROR": 400,
        "NOT_FOUND": 404,
        "PROCESSING_ERROR": 500,
        "STORAGE_ERROR": 500,
    }
    status_code = status_map.get(exc.code, 400)
    return create_error_response(exc, status_code)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global exception handler for HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": {}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for general exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)}
            }
        }
    )
