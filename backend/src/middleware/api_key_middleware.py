"""Middleware enforcing X-API-Key authentication for embedding routes."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class EmbeddingAPIKeyMiddleware(BaseHTTPMiddleware):
    """Simple API-key middleware scoped to /api/v1/embedding endpoints.
    
    Note: This middleware is ONLY active when EMBEDDING_CLIENT_API_KEY is set.
    For development, leave it unset to disable authentication.
    """

    def __init__(self, app, protected_prefix: str = "/api/v1/embedding"):
        super().__init__(app)
        self.protected_prefix = protected_prefix
        self.expected_key = os.getenv("EMBEDDING_CLIENT_API_KEY")
        
        # Log authentication status
        if self.expected_key:
            print(f"⚠️  Embedding API authentication ENABLED for {protected_prefix}")
        else:
            print(f"✅ Embedding API authentication DISABLED (dev mode)")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Skip authentication if EMBEDDING_CLIENT_API_KEY is not configured
        if not self.expected_key:
            return await call_next(request)

        # Only check embedding endpoints
        if request.url.path.startswith(self.protected_prefix):
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != self.expected_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "AUTHENTICATION_ERROR",
                            "message": "Invalid or missing X-API-Key header",
                        }
                    },
                )

        return await call_next(request)
