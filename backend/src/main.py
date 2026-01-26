"""FastAPI application entry point."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .middleware.api_key_middleware import EmbeddingAPIKeyMiddleware
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
    
    # Import all models to ensure they are registered with SQLAlchemy
    from .models import document, processing_result, chunk, chunking_result
    from .models import chunking_strategy, chunking_task, embedding_models
    from .models import vector_index, index_statistics, query_history
    from .models import search, generation, loading_task
    from .models import parent_chunk, hybrid_chunking_config  # New models for chunking optimization
    
    # Initialize database tables
    init_db()
    
    # Initialize default strategies
    db = SessionLocal()
    try:
        init_default_strategies(db)
    finally:
        db.close()
    
    # 异步初始化 Docling Serve 可用性状态
    from .providers.loaders.docling_serve_client import docling_serve_loader
    if docling_serve_loader:
        try:
            available = await docling_serve_loader.is_available_async()
            print(f"Docling Serve status: {'available' if available else 'unavailable'}")
        except Exception as e:
            print(f"Docling Serve check failed: {e}")
    
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

frontend_origins_env = os.getenv("FRONTEND_ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip()
    for origin in frontend_origins_env.split(",")
    if origin.strip()
] or ["http://localhost:5173", "http://localhost:4173"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Embedding API key middleware (only active when EMBEDDING_CLIENT_API_KEY is set)
app.add_middleware(EmbeddingAPIKeyMiddleware)

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
    from .providers.loaders.docling_serve_client import docling_serve_loader
    
    # 使用异步方法检查 Docling Serve 状态，避免阻塞事件循环
    docling_status = "unavailable"
    docling_available = False
    
    if docling_serve_loader:
        # 使用异步方法，只调用一次
        docling_available = await docling_serve_loader.is_available_async()
        if docling_available:
            docling_status = "ready"
    
    return {
        "success": True,
        "status": "healthy",
        "service": "document-processing-api",
        "components": {
            "docling_serve": {
                "status": docling_status,
                "available": docling_available,
                "ready": docling_available
            }
        }
    }


@app.get("/api/v1/health")
async def api_health_check():
    """API health check endpoint."""
    return await health_check()


# Import and register API routers
from .api import documents, loading, processing, chunking
from .api import chunking_preview, chunking_history, chunking_recommend
from .api import embedding_routes, embedding_query_routes
from .api import vector_index
from .api import search
from .api import generation
from .api import upload_chunked

app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(upload_chunked.router, prefix="/api/v1", tags=["Chunked Upload"])
app.include_router(loading.router, prefix="/api/v1/processing", tags=["Processing - Load"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["Processing - Results"])
app.include_router(chunking.router, prefix="/api/v1/chunking", tags=["Chunking"])
app.include_router(chunking_preview.router, prefix="/api/v1/chunking", tags=["Chunking - Preview"])
app.include_router(chunking_history.router, prefix="/api/v1/chunking", tags=["Chunking - History"])
app.include_router(chunking_recommend.router, prefix="/api/v1", tags=["Chunking - Recommendation"])
app.include_router(embedding_routes.router, prefix="/api/v1", tags=["Embedding"])
app.include_router(embedding_query_routes.router, prefix="/api/v1", tags=["Embedding - Queries"])
app.include_router(vector_index.router, prefix="/api", tags=["Vector Index"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(generation.router, prefix="/api/v1", tags=["Generation"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL
    )
