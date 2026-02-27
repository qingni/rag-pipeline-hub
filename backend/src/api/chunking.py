"""Chunking API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ..storage.database import get_db
from ..services.chunking_service import chunking_service
from ..models.document import Document
from ..models.chunking_strategy import ChunkingStrategy
from ..models.chunking_task import ChunkingTask, StrategyType, TaskStatus
from ..models.chunking_result import ChunkingResult
from ..utils.formatters import success_response, paginated_response, sanitize_statistics
from ..utils.error_handlers import NotFoundError, ValidationError
import json

router = APIRouter()


# Request/Response Models
class ChunkingRequest(BaseModel):
    """Request model for chunking operation."""
    document_id: str = Field(..., description="Document ID to chunk")
    strategy_type: str = Field(..., description="Chunking strategy type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")


class ChunkingTaskResponse(BaseModel):
    """Response model for chunking task."""
    task_id: str
    status: str
    document_id: str
    strategy_type: str
    parameters: Dict[str, Any]
    queue_position: Optional[int] = None


# T015: GET /api/documents/parsed - Get list of loaded documents (ready for chunking)
@router.get("/documents/parsed")
async def get_parsed_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by filename"),
    format: Optional[str] = Query(None, description="Filter by file format"),
    sort_by: str = Query("upload_time", regex="^(filename|upload_time|size_bytes)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Get list of documents that have been loaded and are ready for chunking.
    Simplified workflow: load -> chunk (parse step is optional for future optimization).
    
    Args:
        page: Page number
        page_size: Items per page
        search: Search query for filename
        format: Filter by file format (e.g., 'pdf', 'docx', 'txt')
        sort_by: Sort field (filename, upload_time, size_bytes)
        sort_order: Sort order (asc, desc)
        db: Database session
        
    Returns:
        Paginated list of loaded documents with their processing results
    """
    from ..models.processing_result import ProcessingResult
    from sqlalchemy import and_, or_, desc, asc
    
    # Query documents that have either load or parse results (both can be chunked)
    query = db.query(Document).join(
        ProcessingResult,
        Document.id == ProcessingResult.document_id
    ).filter(
        or_(
            and_(
                ProcessingResult.processing_type == "load",
                ProcessingResult.status == "completed"
            ),
            and_(
                ProcessingResult.processing_type == "parse",
                ProcessingResult.status == "completed"
            )
        )
    ).distinct()
    
    # Apply search filter
    if search:
        query = query.filter(Document.filename.ilike(f"%{search}%"))
    
    # Apply format filter
    if format:
        query = query.filter(Document.format == format.lower())
    
    # Apply sorting
    sort_field = getattr(Document, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    total = query.count()
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()
    
    # For each document, get its latest loading result
    items = []
    for doc in documents:
        # Get loading result
        loading_result = db.query(ProcessingResult).filter(
            ProcessingResult.document_id == doc.id,
            ProcessingResult.processing_type == "load",
            ProcessingResult.status == "completed"
        ).order_by(ProcessingResult.created_at.desc()).first()
        
        if loading_result:
            items.append({
                "id": doc.id,
                "filename": doc.filename,
                "format": doc.format,
                "size_bytes": doc.size_bytes,
                "upload_time": doc.upload_time.isoformat() if doc.upload_time else None,
                "processing_type": "loaded",
                "provider": loading_result.provider,  # 添加加载器名称
                "processing_result": {
                    "id": loading_result.id,
                    "result_path": loading_result.result_path,
                    "created_at": loading_result.created_at.isoformat() if loading_result.created_at else None
                }
            })
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )


# T016: GET /api/chunking/strategies - Get available chunking strategies
@router.get("/strategies")
async def get_chunking_strategies(
    active_only: bool = Query(True, description="Only return active strategies"),
    db: Session = Depends(get_db)
):
    """
    Get list of available chunking strategies.
    
    Args:
        active_only: Filter to only active strategies
        db: Database session
        
    Returns:
        List of chunking strategies
    """
    query = db.query(ChunkingStrategy)
    
    if active_only:
        query = query.filter(ChunkingStrategy.is_enabled == True)
    
    strategies = query.order_by(ChunkingStrategy.strategy_id).all()
    
    items = []
    for strategy in strategies:
        items.append({
            "id": strategy.strategy_id,
            "name": strategy.strategy_name,
            "type": strategy.strategy_type.value,
            "description": strategy.description,
            "default_parameters": strategy.default_params,
            "is_active": strategy.is_enabled
        })
    
    return success_response(data={"strategies": items})


# NEW: GET /api/chunking/format-params - Get format-aware chunking parameters
@router.get("/format-params")
async def get_format_chunking_params(
    document_format: Optional[str] = Query(None, description="Document format (e.g., 'pdf', 'csv', 'docx')"),
    char_count: Optional[int] = Query(None, ge=0, description="Document character count for adaptive params")
):
    """
    获取基于文档格式的推荐分块参数。
    
    Args:
        document_format: 文档格式（如 'pdf', 'csv', 'docx'），不提供则返回所有格式配置
        char_count: 文档字符数，提供后会返回自适应调整的参数
        
    Returns:
        推荐的分块参数配置
    """
    from ..config.smart_params import (
        FORMAT_BASE_PARAMS,
        get_base_text_params,
        get_adaptive_text_params,
        get_all_format_params
    )
    
    # 如果没有指定格式，返回所有格式的配置
    if not document_format:
        # 构建格式参数摘要
        format_summary = get_all_format_params()
        
        # 添加重叠比例
        for fmt, config in format_summary.items():
            chunk_size = config.get("chunk_size", 500)
            overlap = config.get("overlap", 0)
            config["overlap_ratio"] = f"{overlap / chunk_size * 100:.1f}%" if chunk_size > 0 else "0%"
        
        return success_response(
            data={
                "formats": format_summary,
                "categories": {
                    "structured_data": ["csv", "xlsx", "xls", "json"],
                    "long_documents": ["pdf", "docx", "doc"],
                    "plain_text": ["txt", "md"],
                    "web_content": ["html", "htm"],
                    "presentations": ["pptx", "ppt"]
                }
            },
            message="所有文档格式的推荐分块参数"
        )
    
    # 获取指定格式的参数
    fmt = document_format.lower()
    base_params = get_base_text_params(fmt)
    
    result = {
        "format": fmt,
        "base_params": {
            "chunk_size": base_params["chunk_size"],
            "overlap": base_params["overlap"],
            "overlap_ratio": f"{base_params['overlap'] / base_params['chunk_size'] * 100:.1f}%" if base_params["chunk_size"] > 0 else "0%",
            "description": base_params.get("description", "")
        }
    }
    
    # 如果提供了字符数，计算自适应参数
    if char_count is not None:
        adaptive_params = get_adaptive_text_params(fmt, char_count)
        result["adaptive_params"] = {
            "chunk_size": adaptive_params["chunk_size"],
            "overlap": adaptive_params["overlap"],
            "overlap_ratio": f"{adaptive_params['overlap'] / adaptive_params['chunk_size'] * 100:.1f}%" if adaptive_params["chunk_size"] > 0 else "0%",
            "char_count": char_count,
            "length_category": adaptive_params.get("length_category", "medium"),
            "adjustment_note": adaptive_params.get("adjustment_reason", "")
        }
    
    return success_response(
        data=result,
        message=f"文档格式 {fmt.upper()} 的推荐分块参数"
    )


# NEW: GET /api/chunking/smart-params - Get smart parameters for a specific strategy
@router.get("/smart-params")
async def get_smart_chunking_params(
    strategy_type: str = Query(..., description="Strategy type (character, paragraph, heading, semantic, parent_child, hybrid)"),
    document_format: str = Query("default", description="Document format (e.g., 'pdf', 'csv', 'docx')"),
    char_count: int = Query(10000, ge=0, description="Document character count"),
    embedding_model: str = Query("bge-m3", description="Embedding model for semantic strategies"),
    code_block_ratio: float = Query(0.0, ge=0, le=1, description="Code block ratio (0-1)"),
    table_count: int = Query(0, ge=0, description="Number of tables in document"),
    image_count: int = Query(0, ge=0, description="Number of images in document"),
    heading_count: int = Query(0, ge=0, description="Number of headings in document")
):
    """
    获取指定策略的智能参数配置。
    
    根据策略类型和文档特征，返回基于业界最佳实践的最优参数配置。
    
    Args:
        strategy_type: 策略类型
        document_format: 文档格式
        char_count: 文档字符数
        embedding_model: Embedding 模型（用于语义相关策略）
        code_block_ratio: 代码块占比
        table_count: 表格数量
        image_count: 图片数量
        heading_count: 标题数量
        
    Returns:
        策略对应的智能参数配置
    """
    from ..config.smart_params import get_smart_params, get_document_length_category
    
    # 验证策略类型
    valid_strategies = ["character", "paragraph", "heading", "semantic", "parent_child", "hybrid"]
    if strategy_type.lower() not in valid_strategies:
        raise ValidationError(f"Invalid strategy type: {strategy_type}. Must be one of: {', '.join(valid_strategies)}")
    
    # 获取智能参数
    smart_params = get_smart_params(
        strategy_type=strategy_type.lower(),
        doc_format=document_format,
        char_count=char_count,
        embedding_model=embedding_model,
        code_block_ratio=code_block_ratio,
        table_count=table_count,
        image_count=image_count,
        heading_count=heading_count
    )
    
    # 添加文档长度分类信息
    length_category = get_document_length_category(char_count)
    
    return success_response(
        data={
            "strategy_type": strategy_type.lower(),
            "document_context": {
                "format": document_format,
                "char_count": char_count,
                "length_category": length_category.value,
                "embedding_model": embedding_model,
                "code_block_ratio": code_block_ratio,
                "table_count": table_count,
                "image_count": image_count,
                "heading_count": heading_count
            },
            "recommended_params": smart_params
        },
        message=f"策略 {strategy_type} 的智能参数配置"
    )


# NEW: GET /api/chunking/embedding-params - Get embedding model specific parameters
@router.get("/embedding-params")
async def get_embedding_model_params(
    embedding_model: Optional[str] = Query(None, description="Embedding model name (bge-m3, qwen3-embedding-8b)")
):
    """
    获取 Embedding 模型特定的语义分块参数。
    
    不同的 Embedding 模型有不同的最优相似度阈值和块大小范围。
    
    Args:
        embedding_model: Embedding 模型名称，不提供则返回所有模型配置
        
    Returns:
        Embedding 模型的语义分块参数配置
    """
    from ..config.smart_params import EMBEDDING_MODEL_PARAMS, get_semantic_params
    
    if not embedding_model:
        # 返回所有模型配置
        return success_response(
            data={
                "models": EMBEDDING_MODEL_PARAMS,
                "recommended": "bge-m3",
                "recommendation_reason": "BGE-M3 在速度和精度之间取得良好平衡，适合大多数场景"
            },
            message="所有 Embedding 模型的语义分块参数配置"
        )
    
    # 获取指定模型的参数
    model_name = embedding_model.lower()
    if model_name not in EMBEDDING_MODEL_PARAMS:
        available_models = list(EMBEDDING_MODEL_PARAMS.keys())
        raise ValidationError(f"Unknown embedding model: {embedding_model}. Available: {', '.join(available_models)}")
    
    params = get_semantic_params(model_name)
    
    return success_response(
        data={
            "model": model_name,
            "params": params,
            "usage_tips": _get_embedding_usage_tips(model_name)
        },
        message=f"Embedding 模型 {model_name} 的语义分块参数配置"
    )


def _get_embedding_usage_tips(model_name: str) -> str:
    """获取 Embedding 模型使用建议"""
    tips = {
        "bge-m3": "推荐用于大多数场景，速度快，1024维向量。适合中等长度文档。",
        "qwen3-embedding-8b": "适合需要高精度的场景，4096维向量，支持32K上下文。适合超长文档和复杂语义。",
        "default": "默认配置，适用于未知模型。"
    }
    return tips.get(model_name, tips["default"])


# T028: POST /api/chunking/chunk - Create chunking task
@router.post("/chunk")
async def create_chunking_task(
    request: ChunkingRequest,
    overwrite_mode: str = Query("auto", regex="^(auto|always|never)$", description="Overwrite mode: auto (smart), always (force overwrite), never (always create new)"),
    db: Session = Depends(get_db)
):
    """
    Create a new chunking task with intelligent version management.
    
    Args:
        request: Chunking request
        overwrite_mode: Overwrite strategy
            - auto: Smart detection (minor changes overwrite, major changes create new)
            - always: Always overwrite existing result for same strategy
            - never: Always create new result (maintain full history)
        db: Database session
        
    Returns:
        Created task information
    """
    # Validate document exists
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise NotFoundError("Document", request.document_id)
    
    # Check if document has been processed (load or parse)
    from ..models.processing_result import ProcessingResult
    from sqlalchemy import or_, and_
    
    processing_result = db.query(ProcessingResult).filter(
        ProcessingResult.document_id == request.document_id,
        or_(
            and_(
                ProcessingResult.processing_type == "parse",
                ProcessingResult.status == "completed"
            ),
            and_(
                ProcessingResult.processing_type == "load",
                ProcessingResult.status == "completed"
            )
        )
    ).order_by(ProcessingResult.created_at.desc()).first()
    
    if not processing_result:
        raise ValidationError(f"Document {request.document_id} must be loaded first")
    
    # Convert strategy_type string to enum
    try:
        strategy_enum = StrategyType[request.strategy_type.upper()]
    except KeyError:
        raise ValidationError(f"Invalid strategy type: {request.strategy_type}")
    
    # Validate strategy exists
    strategy = db.query(ChunkingStrategy).filter(
        ChunkingStrategy.strategy_type == strategy_enum,
        ChunkingStrategy.is_enabled == True
    ).first()
    
    if not strategy:
        raise ValidationError(f"Strategy '{request.strategy_type}' not found or inactive")
    
    # Validate parameters
    validated_params = chunking_service.validate_strategy_parameters(
        request.strategy_type,
        request.parameters
    )
    
    # Import version helper
    from ..utils.chunking_version_helper import ChunkingVersionHelper
    
    # Check for existing results with same document + strategy
    import json
    from ..models.chunking_result import ChunkingResult, ResultStatus
    import logging
    
    logger = logging.getLogger(__name__)
    params_json = json.dumps(validated_params, sort_keys=True)
    logger.info(f"Creating chunking task - Document: {request.document_id}, Strategy: {strategy_enum.value}, Params: {params_json}, OverwriteMode: {overwrite_mode}")
    
    # Query all completed results for this document + strategy (active only)
    existing_results = db.query(ChunkingResult).join(
        ChunkingTask,
        ChunkingResult.task_id == ChunkingTask.task_id
    ).filter(
        ChunkingTask.source_document_id == request.document_id,
        ChunkingTask.chunking_strategy == strategy_enum,
        ChunkingResult.status == ResultStatus.COMPLETED,
        ChunkingResult.is_active == True
    ).order_by(ChunkingResult.created_at.desc()).all()
    
    # Decision logic based on overwrite_mode
    should_overwrite = False
    overwrite_reason = None
    existing_result_to_replace = None
    
    if existing_results:
        latest_result = existing_results[0]
        existing_params_json = json.dumps(latest_result.chunking_params, sort_keys=True)
        
        logger.info(f"Found {len(existing_results)} existing active result(s)")
        logger.info(f"Latest result ID: {latest_result.result_id}, Params: {existing_params_json}")
        
        # Check if parameters are exactly the same
        if existing_params_json == params_json:
            logger.info(f"Parameters match exactly, reusing existing result: {latest_result.result_id}")
            # Return existing result info
            existing_task = db.query(ChunkingTask).filter(
                ChunkingTask.task_id == latest_result.task_id
            ).first()
            
            return success_response(
                data={
                    "task_id": existing_task.task_id,
                    "status": existing_task.status.value,
                    "document_id": existing_task.source_document_id,
                    "strategy_type": existing_task.chunking_strategy.value,
                    "parameters": existing_task.chunking_params,
                    "queue_position": existing_task.queue_position,
                    "result_id": latest_result.result_id,
                    "total_chunks": latest_result.total_chunks,
                    "version": latest_result.version,
                    "is_active": latest_result.is_active,
                    "created_at": existing_task.created_at.isoformat() if existing_task.created_at else None
                },
                message="Using existing chunking result (identical parameters)"
            )
        
        # Parameters differ - apply overwrite mode logic
        if overwrite_mode == "always":
            should_overwrite = True
            overwrite_reason = "Manual override: always overwrite mode"
            existing_result_to_replace = latest_result
            logger.info(f"Overwrite mode 'always': will replace result {latest_result.result_id}")
        
        elif overwrite_mode == "auto":
            # Intelligent detection
            is_minor, reason = ChunkingVersionHelper.is_minor_param_change(
                latest_result.chunking_params,
                validated_params
            )
            
            if is_minor:
                should_overwrite = True
                overwrite_reason = f"Auto-optimization: {reason}"
                existing_result_to_replace = latest_result
                logger.info(f"Auto mode detected minor change: will replace result {latest_result.result_id}. Reason: {reason}")
            else:
                should_overwrite = False
                logger.info(f"Auto mode detected major change: will create new result. Reason: {reason}")
        
        elif overwrite_mode == "never":
            should_overwrite = False
            logger.info("Overwrite mode 'never': creating new result")
    
    # Handle overwrite: deactivate old result
    new_version = 1
    previous_version_id = None
    
    if should_overwrite and existing_result_to_replace:
        # Calculate version
        max_version = db.query(func.max(ChunkingResult.version)).filter(
            ChunkingResult.document_id == request.document_id,
            ChunkingResult.chunking_strategy == strategy_enum
        ).scalar() or 0
        
        new_version = max_version + 1
        previous_version_id = existing_result_to_replace.result_id
        
        # Deactivate old result
        existing_result_to_replace.is_active = False
        db.flush()
        logger.info(f"Deactivated result {existing_result_to_replace.result_id}, new version: {new_version}")
    else:
        # Calculate version for new result
        max_version = db.query(func.max(ChunkingResult.version)).filter(
            ChunkingResult.document_id == request.document_id,
            ChunkingResult.chunking_strategy == strategy_enum
        ).scalar() or 0
        
        new_version = max_version + 1
        logger.info(f"Creating new result version {new_version}")
    
    # Create task (but don't commit yet - wait for processing to succeed)
    task = ChunkingTask(
        source_document_id=request.document_id,
        source_file_path=document.storage_path,
        chunking_strategy=strategy_enum,
        chunking_params=validated_params,
        status=TaskStatus.PENDING,
        queue_position=0  # Will be set by queue manager
    )
    
    db.add(task)
    db.flush()  # Flush to get task_id without committing
    
    # Process task immediately (queue management will be added in Phase 5)
    try:
        result = chunking_service.process_chunking_task(
            task.task_id, 
            db, 
            version=new_version,
            previous_version_id=previous_version_id,
            replacement_reason=overwrite_reason
        )
        db.refresh(task)
        
        # Only commit if processing succeeded
        if task.status == TaskStatus.COMPLETED:
            db.commit()
            
            message = "Chunking task created and completed successfully"
            if should_overwrite:
                message = f"Chunking completed (replaced version {existing_result_to_replace.version})"
            
            return success_response(
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "document_id": task.source_document_id,
                    "strategy_type": task.chunking_strategy.value,
                    "parameters": task.chunking_params,
                    "queue_position": task.queue_position,
                    "result_id": result.result_id if result else None,
                    "total_chunks": result.total_chunks if result else 0,
                    "version": result.version if result else new_version,
                    "is_active": result.is_active if result else True,
                    "previous_version_id": result.previous_version_id if result else None,
                    "replacement_reason": result.replacement_reason if result else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                },
                message=message
            )
        else:
            # Task failed, rollback to avoid creating failed task record
            db.rollback()
            raise ValidationError(
                f"Chunking task failed: {task.error_message or 'Unknown error'}"
            )
    except Exception as e:
        # Rollback transaction to avoid creating failed task record
        db.rollback()
        error_msg = str(e)
        if hasattr(e, 'message'):
            error_msg = e.message
        raise ValidationError(f"Failed to process chunking task: {error_msg}")
    
    return success_response(
        data={
            "task_id": task.task_id,
            "status": task.status.value,
            "document_id": task.source_document_id,
            "strategy_type": task.chunking_strategy.value,
            "parameters": task.chunking_params,
            "queue_position": task.queue_position,
            "created_at": task.created_at.isoformat() if task.created_at else None
        },
        message="Chunking task created successfully"
    )


# T029: GET /api/chunking/task/{task_id} - Get task status
@router.get("/task/{task_id}")
async def get_chunking_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get chunking task status and details.
    
    Args:
        task_id: Task identifier
        db: Database session
        
    Returns:
        Task information
    """
    task = db.query(ChunkingTask).filter(ChunkingTask.task_id == task_id).first()
    if not task:
        raise NotFoundError("ChunkingTask", task_id)
    
    # Get associated result if completed
    result = None
    if task.status.value == "completed":
        result = db.query(ChunkingResult).filter(
            ChunkingResult.task_id == task_id
        ).first()
    
    response_data = {
        "task_id": task.task_id,
        "status": task.status.value,
        "document_id": task.source_document_id,
        "strategy_type": task.chunking_strategy.value,
        "parameters": task.chunking_params,
        "queue_position": task.queue_position,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result_id": None,
        "total_chunks": 0
    }
    
    if result:
        response_data["result_id"] = result.result_id
        response_data["total_chunks"] = result.total_chunks
    
    return success_response(data=response_data)


# Get latest chunking result for a document (optionally filtered by strategy and parameters)
@router.get("/result/latest/{document_id}")
async def get_latest_result_for_document(
    document_id: str,
    strategy_type: Optional[str] = Query(None, description="Filter by strategy type"),
    parameters: Optional[str] = Query(None, description="Filter by parameters (JSON string)"),
    db: Session = Depends(get_db)
):
    """
    Get the latest active chunking result for a document.
    Can optionally filter by strategy type and/or parameters.
    
    Args:
        document_id: Document ID
        strategy_type: Optional strategy type filter
        parameters: Optional parameters filter (JSON string)
        db: Database session
        
    Returns:
        Latest chunking result or null if none exists
    """
    from ..models.chunking_result import ResultStatus
    
    # Start with base query for this document
    query = db.query(ChunkingResult).join(
        ChunkingTask,
        ChunkingResult.task_id == ChunkingTask.task_id
    ).filter(
        ChunkingTask.source_document_id == document_id,
        ChunkingResult.status == ResultStatus.COMPLETED,
        ChunkingResult.is_active == True
    )
    
    # Apply strategy filter if provided
    if strategy_type:
        try:
            strategy_enum = StrategyType[strategy_type.upper()]
            query = query.filter(ChunkingTask.chunking_strategy == strategy_enum)
        except KeyError:
            raise ValidationError(f"Invalid strategy type: {strategy_type}")
    
    # Apply parameters filter if provided
    if parameters:
        try:
            import json
            params_dict = json.loads(parameters)
            params_json = json.dumps(params_dict, sort_keys=True)
            
            # Filter by exact parameter match
            query = query.filter(
                func.json_extract(ChunkingResult.chunking_params, '$') == params_json
            )
        except json.JSONDecodeError:
            raise ValidationError("Invalid parameters JSON")
    
    # Get the most recent result
    result = query.order_by(ChunkingResult.created_at.desc()).first()
    
    if not result:
        return success_response(
            data=None,
            message="No chunking results found for this document"
        )
    
    # Get associated task info
    task = db.query(ChunkingTask).filter(ChunkingTask.task_id == result.task_id).first()
    
    return success_response(
        data={
            "result_id": result.result_id,
            "task_id": result.task_id,
            "document_id": result.document_id,
            "document_name": result.document_name,
            "strategy_type": result.chunking_strategy.value,
            "parameters": result.chunking_params,
            "status": result.status.value,
            "total_chunks": result.total_chunks,
            "statistics": sanitize_statistics(result.statistics),
            "version": result.version,
            "is_active": result.is_active,
            "processing_time": result.processing_time,
            "created_at": result.created_at.isoformat() if result.created_at else None
        }
    )


# T030: GET /api/chunking/result/{result_id} - Get chunking result
@router.get("/result/{result_id}")
async def get_chunking_result(
    result_id: str,
    include_chunks: bool = Query(True, description="Include chunk data"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get chunking result with optional chunk data.
    
    Args:
        result_id: Result identifier
        include_chunks: Whether to include chunk content
        page: Page number for chunks
        page_size: Chunks per page
        db: Database session
        
    Returns:
        Chunking result with optional chunks
    """
    result = db.query(ChunkingResult).filter(ChunkingResult.result_id == result_id).first()
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Get document info
    document = db.query(Document).filter(Document.id == result.document_id).first()
    
    response_data = {
        "result_id": result.result_id,
        "task_id": result.task_id,
        "document_id": result.document_id,
        "document_name": result.document_name,
        "strategy_type": result.chunking_strategy.value,
        "parameters": result.chunking_params,
        "status": result.status.value,
        "total_chunks": result.total_chunks,
        "statistics": sanitize_statistics(result.statistics),
        "file_path": result.json_file_path,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }
    
    if include_chunks and result.status.value == "completed":
        from ..models.chunk import Chunk
        
        # Get paginated chunks
        query = db.query(Chunk).filter(Chunk.result_id == result_id).order_by(Chunk.sequence_number)
        total_chunks = query.count()
        offset = (page - 1) * page_size
        chunks = query.offset(offset).limit(page_size).all()
        
        chunk_list = []
        for chunk in chunks:
            chunk_list.append({
                "id": chunk.id,
                "sequence_number": chunk.sequence_number,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type,
                "metadata": chunk.chunk_metadata,
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "token_count": chunk.token_count
            })
        
        response_data["chunks"] = paginated_response(
            items=chunk_list,
            total=total_chunks,
            page=page,
            page_size=page_size
        )
    
    return success_response(data=response_data)


# T026: GET /api/chunking/result/{result_id}/parents - Get parent chunks
@router.get("/result/{result_id}/parents")
async def get_parent_chunks(
    result_id: str,
    include_children: bool = Query(False, description="Include child chunks in response"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get parent chunks for a parent-child chunking result.
    
    Args:
        result_id: Result identifier
        include_children: Whether to include child chunk previews
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        List of parent chunks with optional children
    """
    from ..models.parent_chunk import ParentChunk
    
    # Verify result exists
    result = db.query(ChunkingResult).filter(ChunkingResult.result_id == result_id).first()
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Query parent chunks
    query = db.query(ParentChunk).filter(
        ParentChunk.result_id == result_id
    ).order_by(ParentChunk.sequence_number)
    
    total = query.count()
    
    if total == 0:
        return success_response(
            data=paginated_response(
                items=[],
                total=0,
                page=page,
                page_size=page_size
            ),
            message="No parent chunks found (not a parent-child chunking result)"
        )
    
    offset = (page - 1) * page_size
    parent_chunks = query.offset(offset).limit(page_size).all()
    
    items = []
    for parent in parent_chunks:
        parent_data = parent.to_dict(include_children=include_children)
        items.append(parent_data)
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )


# T027: GET /api/chunking/result/{result_id}/chunks - Get chunks with parent filter
@router.get("/result/{result_id}/chunks")
async def get_result_chunks(
    result_id: str,
    parent_id: Optional[str] = Query(None, description="Filter by parent chunk ID"),
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type (text, table, image, code)"),
    include_parent: bool = Query(False, description="Include parent chunk content"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get chunks from a chunking result with filtering options.
    
    Args:
        result_id: Result identifier
        parent_id: Optional parent chunk ID filter
        chunk_type: Optional chunk type filter
        include_parent: Include parent chunk content for each chunk
        page: Page number
        page_size: Chunks per page
        db: Database session
        
    Returns:
        Paginated list of chunks
    """
    from ..models.chunk import Chunk, ChunkType
    from ..models.parent_chunk import ParentChunk
    
    # Verify result exists
    result = db.query(ChunkingResult).filter(ChunkingResult.result_id == result_id).first()
    if not result:
        raise NotFoundError("ChunkingResult", result_id)
    
    # Build query
    query = db.query(Chunk).filter(Chunk.result_id == result_id)
    
    # Apply parent filter
    if parent_id:
        query = query.filter(Chunk.parent_id == parent_id)
    
    # Apply chunk type filter
    if chunk_type:
        try:
            type_enum = ChunkType[chunk_type.upper()]
            query = query.filter(Chunk.chunk_type == type_enum)
        except KeyError:
            raise ValidationError(f"Invalid chunk type: {chunk_type}. Must be one of: text, table, image, code")
    
    query = query.order_by(Chunk.sequence_number)
    
    total = query.count()
    offset = (page - 1) * page_size
    chunks = query.offset(offset).limit(page_size).all()
    
    # Build response
    items = []
    for chunk in chunks:
        chunk_data = {
            "id": chunk.id,
            "sequence_number": chunk.sequence_number,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type.value if chunk.chunk_type else "text",
            "parent_id": chunk.parent_id,
            "metadata": chunk.chunk_metadata,
            "start_position": chunk.start_position,
            "end_position": chunk.end_position,
            "token_count": chunk.token_count
        }
        
        # Include parent content if requested
        if include_parent and chunk.parent_id:
            parent = db.query(ParentChunk).filter(ParentChunk.id == chunk.parent_id).first()
            if parent:
                chunk_data["parent"] = {
                    "id": parent.id,
                    "sequence_number": parent.sequence_number,
                    "content": parent.content,
                    "content_preview": parent.content[:200] + "..." if len(parent.content) > 200 else parent.content
                }
        
        items.append(chunk_data)
    
    return success_response(
        data=paginated_response(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )
