"""FastAPI application entry point."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .utils.error_handlers import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    general_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting up application...")
    from .storage.database import init_db, SessionLocal
    from .utils.init_strategies import init_default_strategies
    
    # Initialize database tables
    init_db()
    
    # Initialize default strategies
    db = SessionLocal()
    try:
        init_default_strategies(db)
    finally:
        db.close()
    
    print("Application startup complete")
    
    yield
    
    # Shutdown
    print("Shutting down application...")


# Create FastAPI application
app = FastAPI(
    title="文档处理和检索系统 API",
    description="Document processing and retrieval system with AI capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
from .api import documents, loading, parsing, processing, chunking
from .api import chunking_preview, chunking_history

app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(loading.router, prefix="/api/v1/processing", tags=["Processing - Load"])
app.include_router(parsing.router, prefix="/api/v1/processing", tags=["Processing - Parse"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["Processing - Results"])
app.include_router(chunking.router, prefix="/api/v1/chunking", tags=["Chunking"])
app.include_router(chunking_preview.router, prefix="/api/v1/chunking", tags=["Chunking - Preview"])
app.include_router(chunking_history.router, prefix="/api/v1/chunking", tags=["Chunking - History"])

# More routers will be added for embedding, indexing, search, generation


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL
    )
