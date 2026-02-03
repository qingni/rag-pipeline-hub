"""
Embedding model recommendation API.

Provides endpoints for:
- Single document model recommendation
- Batch document model recommendation
- Model capability management
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..services.model_recommend_service import (
    ModelRecommendService,
    get_model_recommend_service,
)
from ..services.model_capability_service import (
    ModelCapabilityService,
    get_model_capability_service,
)
from ..services.document_feature_service import (
    DocumentFeatureService,
    get_document_feature_service,
)


router = APIRouter(prefix="/embedding/recommend", tags=["Embedding Recommendation"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ChunkInput(BaseModel):
    """Chunk data for analysis."""
    chunk_id: str = Field(..., description="Chunk identifier")
    content: str = Field(..., description="Chunk content")
    chunk_type: str = Field(default="text", description="Chunk type: text, image, table, code")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class DocumentInput(BaseModel):
    """Document data for analysis."""
    document_id: str = Field(..., description="Document identifier")
    document_name: str = Field(..., description="Document filename")
    chunks: List[ChunkInput] = Field(..., description="Document chunks")


class SingleRecommendRequest(BaseModel):
    """Request for single document recommendation."""
    document_id: str = Field(..., description="Document identifier")
    document_name: str = Field(..., description="Document filename")
    chunks: List[ChunkInput] = Field(..., description="Document chunks")
    top_n: int = Field(default=3, ge=1, le=10, description="Number of recommendations")


class BatchRecommendRequest(BaseModel):
    """Request for batch document recommendation."""
    documents: List[DocumentInput] = Field(..., min_length=1, max_length=100)
    top_n: int = Field(default=3, ge=1, le=10, description="Number of recommendations")
    outlier_threshold: Optional[float] = Field(
        default=None, 
        ge=0.1, 
        le=0.5,
        description="Threshold for outlier detection (default: 0.3)"
    )


class ModelCapabilityUpdateRequest(BaseModel):
    """Request for updating model capability."""
    language_scores: Optional[dict] = Field(None, description="Language score updates")
    domain_scores: Optional[dict] = Field(None, description="Domain score updates")
    multimodal_score: Optional[float] = Field(None, ge=0, le=1, description="Multimodal score")
    is_enabled: Optional[bool] = Field(None, description="Enable/disable model")
    description: Optional[str] = Field(None, description="Model description")


# ============================================================================
# Dependency Injection
# ============================================================================

def get_recommend_service() -> ModelRecommendService:
    """Get recommendation service."""
    return get_model_recommend_service()


def get_capability_service() -> ModelCapabilityService:
    """Get capability service."""
    return get_model_capability_service()


def get_feature_service() -> DocumentFeatureService:
    """Get feature service."""
    return get_document_feature_service()


# ============================================================================
# Single Document Recommendation
# ============================================================================

@router.post("/single")
async def recommend_for_document(
    request: SingleRecommendRequest,
    service: ModelRecommendService = Depends(get_recommend_service),
):
    """
    Get model recommendation for a single document.
    
    Analyzes document features and returns ranked model recommendations.
    """
    try:
        # Convert chunks to dict format
        chunks = [
            {
                'chunk_id': c.chunk_id,
                'content': c.content,
                'chunk_type': c.chunk_type,
                'metadata': c.metadata,
            }
            for c in request.chunks
        ]
        
        result = service.recommend_for_chunks(
            document_id=request.document_id,
            document_name=request.document_name,
            chunks=chunks,
            top_n=request.top_n,
        )
        
        return result.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}"
        )


# ============================================================================
# Batch Document Recommendation
# ============================================================================

@router.post("/batch")
async def recommend_for_batch(
    request: BatchRecommendRequest,
    service: ModelRecommendService = Depends(get_recommend_service),
):
    """
    Get model recommendation for multiple documents.
    
    Analyzes all documents, provides unified recommendation,
    and identifies outlier documents that may need special handling.
    """
    try:
        # Convert documents to dict format
        documents = [
            {
                'document_id': doc.document_id,
                'document_name': doc.document_name,
                'chunks': [
                    {
                        'chunk_id': c.chunk_id,
                        'content': c.content,
                        'chunk_type': c.chunk_type,
                        'metadata': c.metadata,
                    }
                    for c in doc.chunks
                ],
            }
            for doc in request.documents
        ]
        
        result = service.recommend_for_batch(
            documents=documents,
            top_n=request.top_n,
            outlier_threshold=request.outlier_threshold,
        )
        
        return result.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch recommendation failed: {str(e)}"
        )


# ============================================================================
# Document Feature Analysis
# ============================================================================

@router.post("/analyze")
async def analyze_document_features(
    request: SingleRecommendRequest,
    service: DocumentFeatureService = Depends(get_feature_service),
):
    """
    Analyze document features without recommendation.
    
    Returns detected language, domain, and content statistics.
    """
    try:
        # Convert chunks to dict format
        chunks = [
            {
                'chunk_id': c.chunk_id,
                'content': c.content,
                'chunk_type': c.chunk_type,
                'metadata': c.metadata,
            }
            for c in request.chunks
        ]
        
        analysis = service.analyze_document(
            document_id=request.document_id,
            document_name=request.document_name,
            chunks=chunks,
        )
        
        return analysis.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# ============================================================================
# Model Capability Management
# ============================================================================

@router.get("/models")
async def list_models(
    enabled_only: bool = Query(default=True, description="Only show enabled models"),
    model_type: Optional[str] = Query(default=None, description="Filter by type: text, multimodal"),
    service: ModelCapabilityService = Depends(get_capability_service),
):
    """
    List available embedding models with capabilities.
    """
    try:
        if model_type == "text":
            models = service.get_text_models(enabled_only)
        elif model_type == "multimodal":
            models = service.get_multimodal_models(enabled_only)
        else:
            models = service.get_all_models(enabled_only)
        
        return {
            "models": [m.to_dict() for m in models],
            "count": len(models),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/models/{model_name}")
async def get_model(
    model_name: str,
    service: ModelCapabilityService = Depends(get_capability_service),
):
    """
    Get capability details for a specific model.
    """
    model = service.get_model(model_name)
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found"
        )
    
    return model.to_dict()


@router.put("/models/{model_name}")
async def update_model(
    model_name: str,
    request: ModelCapabilityUpdateRequest,
    service: ModelCapabilityService = Depends(get_capability_service),
):
    """
    Update model capability configuration.
    
    Admin endpoint for customizing model scores.
    """
    # Check if model exists
    model = service.get_model(model_name)
    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found"
        )
    
    # Build updates dict
    updates = {}
    if request.language_scores is not None:
        updates['language_scores'] = request.language_scores
    if request.domain_scores is not None:
        updates['domain_scores'] = request.domain_scores
    if request.multimodal_score is not None:
        updates['multimodal_score'] = request.multimodal_score
    if request.is_enabled is not None:
        updates['is_enabled'] = request.is_enabled
    if request.description is not None:
        updates['description'] = request.description
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    success = service.update_model(model_name, updates)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to update model"
        )
    
    # Return updated model
    updated_model = service.get_model(model_name)
    return {
        "message": f"Model '{model_name}' updated successfully",
        "model": updated_model.to_dict() if updated_model else None,
    }


@router.get("/weights")
async def get_recommendation_weights(
    service: ModelCapabilityService = Depends(get_capability_service),
):
    """
    Get current recommendation algorithm weights.
    """
    weights = service.get_recommendation_weights()
    return {
        "weights": weights,
        "description": {
            "language_match": "语言匹配度权重",
            "domain_match": "领域匹配度权重",
            "multimodal_support": "多模态支持度权重",
        }
    }


@router.post("/reload")
async def reload_configuration(
    service: ModelCapabilityService = Depends(get_capability_service),
):
    """
    Reload model capability configuration from file.
    
    Admin endpoint for applying config changes without restart.
    """
    try:
        service.reload_config()
        models = service.get_all_models(enabled_only=False)
        return {
            "message": "Configuration reloaded successfully",
            "models_loaded": len(models),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload configuration: {str(e)}"
        )
