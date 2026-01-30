"""Chunking recommendation API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import os
import json

from ..services.chunking_recommend_service import get_chunking_recommend_service
from ..config import settings
from ..storage.database import get_db
from ..models.processing_result import ProcessingResult
from ..models.document import Document
from ..utils.formatters import success_response


router = APIRouter(prefix="/chunking", tags=["Recommendation"])


# ============ Request/Response Models ============

class RecommendRequest(BaseModel):
    """Request model for strategy recommendation."""
    document_id: str = Field(..., description="Document ID from loading result")
    top_n: int = Field(default=3, ge=1, le=5, description="Number of recommendations to return")


class AnalyzeRequest(BaseModel):
    """Request model for document analysis."""
    document_id: str = Field(..., description="Document ID from loading result")


class RecommendationItem(BaseModel):
    """Single recommendation item."""
    strategy: str
    strategy_name: str
    reason: str
    confidence: float
    estimated_chunks: int
    estimated_avg_chunk_size: int
    is_top: bool
    rank: int
    suggested_params: Dict[str, Any]
    pros: List[str]
    cons: List[str]


class RecommendResponse(BaseModel):
    """Response model for strategy recommendation."""
    document_id: str
    features: Dict[str, Any]
    recommendations: List[RecommendationItem]
    analysis_time_ms: float


class AnalyzeResponse(BaseModel):
    """Response model for document analysis."""
    document_id: str
    features: Dict[str, Any]


# ============ Helper Functions ============

def get_document_content(document_id: str, db: Session) -> tuple:
    """
    Get document text content from loading result.
    
    Args:
        document_id: Document identifier
        db: Database session
    
    Returns:
        Tuple of (text_content, document_result_dict)
    
    Raises:
        HTTPException: If document not found
    """
    # First, get the document to retrieve original file format
    document = db.query(Document).filter(Document.id == document_id).first()
    
    # Find the processing result from database
    processing_result = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == document_id,
        ProcessingResult.processing_type == "load",
        ProcessingResult.status == "completed"
    ).order_by(ProcessingResult.created_at.desc()).first()
    
    if not processing_result:
        raise HTTPException(
            status_code=404,
            detail=f"No loading result found for document '{document_id}'"
        )
    
    # Get the result file path
    result_path = processing_result.result_path
    if not os.path.isabs(result_path):
        result_path = os.path.join(os.getcwd(), result_path)
    
    if not os.path.exists(result_path):
        raise HTTPException(
            status_code=404,
            detail=f"Loading result file not found: {result_path}"
        )
    
    try:
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
            # Extract text content - support different result formats
            text = result.get("full_text", "") or result.get("content", {}).get("full_text", "") or result.get("content", {}).get("text", "")
            
            # Add original file format from document record (critical for proper strategy recommendation)
            if document:
                result["file_format"] = document.format
                result["file_name"] = document.filename
            
            return text, result
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read loading result: {str(e)}"
        )


# ============ API Endpoints ============

@router.post("/recommend")
async def get_recommendations(request: RecommendRequest, db: Session = Depends(get_db)):
    """
    Get chunking strategy recommendations for a document.
    
    Analyzes document structure and recommends the most suitable
    chunking strategies based on document features.
    """
    # Get document content
    text, document_result = get_document_content(request.document_id, db)
    
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Document has no text content to analyze"
        )
    
    # Get recommendations
    service = get_chunking_recommend_service()
    result = service.recommend(
        text=text,
        document_id=request.document_id,
        document_result=document_result,
        top_n=request.top_n
    )
    
    return success_response(data={
        "document_id": result.document_id,
        "features": result.features,
        "recommendations": [
            {
                "strategy": rec.strategy.value,
                "strategy_name": rec.strategy_name,
                "reason": rec.reason,
                "confidence": rec.confidence,
                "estimated_chunks": rec.estimated_chunks,
                "estimated_avg_chunk_size": rec.estimated_avg_chunk_size,
                "is_top": rec.is_top,
                "rank": rec.rank,
                "suggested_params": rec.suggested_params,
                "pros": rec.pros,
                "cons": rec.cons
            }
            for rec in result.recommendations
        ],
        "analysis_time_ms": result.analysis_time_ms
    })


@router.post("/analyze")
async def analyze_document(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Analyze document structure features.
    
    Returns detailed structural analysis without recommendations.
    """
    # Get document content
    text, document_result = get_document_content(request.document_id, db)
    
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Document has no text content to analyze"
        )
    
    # Analyze document
    service = get_chunking_recommend_service()
    features = service.analyze_document(text, document_result)
    
    # Convert heading_levels keys to strings for JSON serialization
    features_dict = features.to_dict()
    features_dict["heading_levels"] = {
        str(k): v for k, v in features_dict.get("heading_levels", {}).items()
    }
    
    return success_response(data={
        "document_id": request.document_id,
        "features": features_dict
    })
