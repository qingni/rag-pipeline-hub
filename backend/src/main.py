"""FastAPI application entry point."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .utils.error_handlers import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    general_exception_handler
)

# Create FastAPI application
app = FastAPI(
    title="文档处理和检索系统 API",
    description="Document processing and retrieval system with AI capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "success": True,
        "message": "文档处理和检索系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "status": "healthy",
        "service": "document-processing-api"
    }


# Import and register API routers
from .api import documents, loading, parsing, processing

app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(loading.router, prefix="/api/v1/processing", tags=["Processing - Load"])
app.include_router(parsing.router, prefix="/api/v1/processing", tags=["Processing - Parse"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["Processing - Results"])

# More routers will be added for chunking, embedding, indexing, search, generation


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL
    )
