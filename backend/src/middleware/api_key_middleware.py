"""Middleware enforcing X-API-Key authentication for embedding routes."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class EmbeddingAPIKeyMiddleware(BaseHTTPMiddleware):
    """Simple API-key middleware scoped to /api/v1/embedding endpoints."""

    def __init__(self, app, protected_prefix: str = "/api/v1/embedding"):
        super().__init__(app)
        self.protected_prefix = protected_prefix
        self.expected_key = os.getenv("EMBEDDING_CLIENT_API_KEY")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if not self.expected_key:
            return await call_next(request)

        if request.url.path.startswith(self.protected_prefix):
            api_key = request.headers.get("X-API-Key")
            if not api_key or api_key != self.expected_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "AUTHENTICATION_ERROR",
                            "message": "Invalid X-API-Key header",
                        }
                    },
                )

        return await call_next(request)
