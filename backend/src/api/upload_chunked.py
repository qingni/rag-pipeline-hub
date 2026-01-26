"""
Chunked Upload API - 分片上传支持断点续传

功能：
1. 分片上传：将大文件分割为多个小分片上传
2. 断点续传：上传中断后可从断点继续
3. 秒传：通过文件哈希检测相同文件
4. 会话管理：自动清理过期的上传会话
"""
from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional, List
import os
import hashlib
import uuid
import shutil
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..storage.database import get_db
from ..storage.file_storage import file_storage
from ..models.document import Document
from ..utils.formatters import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["chunked-upload"])

# ==================== 配置 ====================

# 分片大小: 5MB
CHUNK_SIZE = 5 * 1024 * 1024

# 上传会话超时: 24小时
SESSION_TIMEOUT = timedelta(hours=24)

# 分片临时存储目录
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
CHUNK_DIR = UPLOAD_DIR / "_chunks"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 数据结构 ====================

@dataclass
class UploadSession:
    """上传会话"""
    upload_id: str
    filename: str
    file_size: int
    file_hash: str
    total_chunks: int
    uploaded_chunks: set = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def chunk_dir(self) -> Path:
        return CHUNK_DIR / self.upload_id
    
    def is_expired(self) -> bool:
        return datetime.now() - self.created_at > SESSION_TIMEOUT
    
    def is_complete(self) -> bool:
        return len(self.uploaded_chunks) == self.total_chunks
    
    @property
    def progress(self) -> float:
        if self.total_chunks == 0:
            return 0
        return len(self.uploaded_chunks) / self.total_chunks * 100
    
    def to_dict(self) -> dict:
        return {
            "upload_id": self.upload_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_hash": self.file_hash,
            "total_chunks": self.total_chunks,
            "uploaded_chunks": sorted(list(self.uploaded_chunks)),
            "uploaded_count": len(self.uploaded_chunks),
            "progress": round(self.progress, 1),
            "is_complete": self.is_complete(),
            "created_at": self.created_at.isoformat()
        }


# 内存中的上传会话记录 (生产环境应使用 Redis)
_upload_sessions: dict[str, UploadSession] = {}


# ==================== 辅助函数 ====================

def get_session(upload_id: str) -> Optional[UploadSession]:
    """获取上传会话"""
    session = _upload_sessions.get(upload_id)
    if session and session.is_expired():
        cleanup_session(session)
        del _upload_sessions[upload_id]
        return None
    return session


def cleanup_session(session: UploadSession) -> None:
    """清理上传会话的临时文件"""
    try:
        if session.chunk_dir.exists():
            shutil.rmtree(session.chunk_dir)
            logger.info(f"Cleaned up session: {session.upload_id}")
    except Exception as e:
        logger.error(f"Failed to cleanup session {session.upload_id}: {e}")


def cleanup_expired_sessions() -> int:
    """清理过期的上传会话"""
    expired = [
        uid for uid, session in _upload_sessions.items()
        if session.is_expired()
    ]
    
    for uid in expired:
        cleanup_session(_upload_sessions[uid])
        del _upload_sessions[uid]
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired upload sessions")
    
    return len(expired)


def find_session_by_hash(file_hash: str) -> Optional[UploadSession]:
    """根据文件哈希查找未完成的上传会话"""
    for session in _upload_sessions.values():
        if session.file_hash == file_hash and not session.is_expired():
            return session
    return None


# ==================== API 端点 ====================

@router.post("/init")
async def init_upload(
    filename: str = Query(..., min_length=1, description="文件名"),
    file_size: int = Query(..., ge=1, description="文件大小 (bytes)"),
    file_hash: str = Query(..., min_length=32, max_length=32, description="文件 MD5 哈希"),
    db: Session = Depends(get_db)
):
    """
    初始化分片上传会话
    
    客户端需要先计算文件的 MD5 哈希，用于：
    1. 检查是否已存在相同文件（秒传）
    2. 验证文件完整性
    3. 断点续传时识别同一文件
    
    Returns:
        - instant_upload: 如果为 True，表示秒传成功
        - resumable: 如果为 True，表示发现未完成的上传可续传
        - upload_id: 上传会话 ID
        - chunk_size: 分片大小
        - total_chunks: 总分片数
    """
    # 1. 检查是否已存在相同哈希的文件（秒传）
    existing_doc = db.query(Document).filter(
        Document.content_hash == file_hash
    ).first()
    
    if existing_doc:
        logger.info(f"Instant upload: file {filename} already exists as {existing_doc.id}")
        return success_response(
            data={
                "instant_upload": True,
                "message": "文件已存在，秒传成功",
                "document": {
                    "id": existing_doc.id,
                    "filename": existing_doc.filename,
                    "format": existing_doc.format,
                    "size_bytes": existing_doc.size_bytes
                }
            },
            message="Instant upload successful"
        )
    
    # 2. 检查是否有未完成的上传会话（断点续传）
    existing_session = find_session_by_hash(file_hash)
    
    if existing_session:
        logger.info(
            f"Resumable upload found: {existing_session.upload_id}, "
            f"progress: {existing_session.progress:.1f}%"
        )
        return success_response(
            data={
                "resumable": True,
                "message": "发现未完成的上传，可以续传",
                "upload_id": existing_session.upload_id,
                "chunk_size": CHUNK_SIZE,
                **existing_session.to_dict()
            },
            message="Resumable upload session found"
        )
    
    # 3. 创建新的上传会话
    upload_id = str(uuid.uuid4())
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    session = UploadSession(
        upload_id=upload_id,
        filename=filename,
        file_size=file_size,
        file_hash=file_hash,
        total_chunks=total_chunks
    )
    
    # 创建分片存储目录
    session.chunk_dir.mkdir(parents=True, exist_ok=True)
    
    _upload_sessions[upload_id] = session
    
    logger.info(
        f"New upload session created: {upload_id}, "
        f"file: {filename}, size: {file_size}, chunks: {total_chunks}"
    )
    
    return success_response(
        data={
            "upload_id": upload_id,
            "chunk_size": CHUNK_SIZE,
            "total_chunks": total_chunks,
            "message": "上传会话已创建"
        },
        message="Upload session created"
    )


@router.post("/{upload_id}/chunk")
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Query(..., ge=0, description="分片索引 (从 0 开始)"),
    chunk: UploadFile = File(..., description="分片数据")
):
    """
    上传单个分片
    
    每个分片最大 5MB，最后一个分片可能小于 5MB
    
    Returns:
        - chunk_index: 已上传的分片索引
        - uploaded_count: 已上传的分片数量
        - total_chunks: 总分片数
        - progress: 上传进度 (0-100)
    """
    session = get_session(upload_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="上传会话不存在或已过期，请重新初始化上传"
        )
    
    if chunk_index >= session.total_chunks:
        raise HTTPException(
            status_code=400,
            detail=f"分片索引超出范围: {chunk_index} >= {session.total_chunks}"
        )
    
    # 读取分片内容
    content = await chunk.read()
    
    # 验证分片大小
    expected_size = CHUNK_SIZE
    if chunk_index == session.total_chunks - 1:
        # 最后一个分片
        expected_size = session.file_size - (chunk_index * CHUNK_SIZE)
    
    if len(content) != expected_size:
        raise HTTPException(
            status_code=400,
            detail=f"分片大小不正确: 期望 {expected_size} 字节, 实际 {len(content)} 字节"
        )
    
    # 保存分片
    chunk_path = session.chunk_dir / f"chunk_{chunk_index:06d}"
    
    with open(chunk_path, "wb") as f:
        f.write(content)
    
    session.uploaded_chunks.add(chunk_index)
    
    logger.debug(f"Chunk uploaded: {upload_id}/{chunk_index}")
    
    return success_response(
        data={
            "chunk_index": chunk_index,
            "uploaded_count": len(session.uploaded_chunks),
            "total_chunks": session.total_chunks,
            "progress": round(session.progress, 1),
            "is_complete": session.is_complete()
        },
        message="Chunk uploaded"
    )


@router.get("/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """
    查询上传状态
    
    返回已上传的分片列表，用于断点续传时确定从哪里继续
    """
    session = get_session(upload_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="上传会话不存在或已过期"
        )
    
    return success_response(
        data=session.to_dict(),
        message="Upload status retrieved"
    )


@router.post("/{upload_id}/complete")
async def complete_upload(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """
    完成上传，合并所有分片
    
    验证所有分片都已上传，合并为完整文件，创建文档记录
    
    Returns:
        - document: 创建的文档信息
    """
    session = get_session(upload_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="上传会话不存在或已过期"
        )
    
    # 检查是否所有分片都已上传
    if not session.is_complete():
        missing = set(range(session.total_chunks)) - session.uploaded_chunks
        return success_response(
            data={
                "complete": False,
                "message": f"还有 {len(missing)} 个分片未上传",
                "missing_chunks": sorted(list(missing)),
                "uploaded_count": len(session.uploaded_chunks),
                "total_chunks": session.total_chunks
            },
            message="Upload incomplete"
        )
    
    # 合并分片
    merged_file_path = CHUNK_DIR / f"{upload_id}_merged"
    
    try:
        logger.info(f"Merging {session.total_chunks} chunks for {upload_id}")
        
        with open(merged_file_path, "wb") as merged:
            for i in range(session.total_chunks):
                chunk_path = session.chunk_dir / f"chunk_{i:06d}"
                with open(chunk_path, "rb") as chunk_file:
                    merged.write(chunk_file.read())
        
        # 验证文件哈希
        with open(merged_file_path, "rb") as f:
            actual_hash = hashlib.md5(f.read()).hexdigest()
        
        if actual_hash != session.file_hash:
            # 清理合并的文件
            merged_file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="文件哈希验证失败，文件可能已损坏，请重新上传"
            )
        
        # 移动到正式存储目录
        with open(merged_file_path, "rb") as f:
            storage_path, content_hash = file_storage.save_upload(
                f, session.filename
            )
        
        # 获取文件信息
        file_size = os.path.getsize(storage_path)
        file_ext = os.path.splitext(session.filename)[1].lower().replace(".", "")
        
        # 创建文档记录
        document = Document(
            filename=session.filename,
            format=file_ext,
            size_bytes=file_size,
            storage_path=storage_path,
            content_hash=content_hash,
            status="uploaded"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 清理临时文件
        merged_file_path.unlink(missing_ok=True)
        cleanup_session(session)
        del _upload_sessions[upload_id]
        
        logger.info(f"Chunked upload completed: {upload_id} -> document {document.id}")
        
        return success_response(
            data={
                "complete": True,
                "document": {
                    "id": document.id,
                    "filename": document.filename,
                    "format": document.format,
                    "size_bytes": document.size_bytes
                }
            },
            message="Upload completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # 清理合并的临时文件
        merged_file_path.unlink(missing_ok=True)
        logger.error(f"Failed to complete upload {upload_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"合并文件失败: {str(e)}"
        )


@router.delete("/{upload_id}/abort")
async def abort_upload(upload_id: str):
    """
    取消上传，清理所有临时分片
    """
    session = _upload_sessions.get(upload_id)
    
    if not session:
        return success_response(
            data={
                "aborted": True,
                "message": "上传会话不存在或已清理"
            },
            message="Upload session not found"
        )
    
    cleanup_session(session)
    del _upload_sessions[upload_id]
    
    logger.info(f"Upload aborted: {upload_id}")
    
    return success_response(
        data={
            "aborted": True,
            "message": "上传已取消，临时文件已清理"
        },
        message="Upload aborted"
    )


@router.get("/sessions")
async def list_upload_sessions(
    limit: int = Query(20, ge=1, le=100, description="最大返回数量")
):
    """
    列出所有上传会话（用于调试）
    """
    # 先清理过期会话
    cleanup_expired_sessions()
    
    sessions = [
        session.to_dict()
        for session in list(_upload_sessions.values())[:limit]
    ]
    
    return success_response(
        data={
            "sessions": sessions,
            "total": len(_upload_sessions),
            "chunk_size": CHUNK_SIZE
        },
        message="Upload sessions listed"
    )


@router.post("/cleanup")
async def trigger_cleanup():
    """
    手动触发清理过期会话
    """
    count = cleanup_expired_sessions()
    
    return success_response(
        data={
            "cleaned": count,
            "remaining": len(_upload_sessions)
        },
        message=f"Cleaned {count} expired sessions"
    )
