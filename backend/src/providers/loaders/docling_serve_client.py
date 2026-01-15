"""
Docling Serve HTTP Client

通过 HTTP API 调用独立部署的 Docling Serve 服务进行文档解析。
替代本地嵌入式 Docling，避免 Backend 启动时的长时间初始化。

支持同步和异步两种调用模式：
- 同步模式：直接调用 /v1/convert/source，等待结果返回
- 异步模式：调用 /v1/convert/file/async，通过轮询获取结果
"""

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base_loader import BaseLoader
from ...models.loading_result import ExtractionQuality

logger = logging.getLogger(__name__)


class DoclingServeLoader(BaseLoader):
    """
    Docling Serve HTTP 客户端
    
    通过 HTTP API 与独立部署的 Docling Serve 服务通信，
    支持同步和异步文档解析。
    """
    
    # 支持的文件格式
    SUPPORTED_FORMATS = {
        'pdf', 'docx', 'doc', 'pptx', 'ppt',
        'xlsx', 'xls', 'html', 'htm', 'md',
        'txt', 'csv', 'png', 'jpg', 'jpeg',
        'tiff', 'tif', 'bmp', 'gif'
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:5001",
        api_key: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        availability_cache_ttl: int = 30  # 可用性缓存过期时间（秒）
    ):
        """
        初始化 Docling Serve 客户端
        
        Args:
            base_url: Docling Serve 服务地址
            api_key: API 密钥（如果服务启用了认证）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            availability_cache_ttl: 可用性缓存过期时间（秒）
        """
        super().__init__(name="docling_serve", quality_level=ExtractionQuality.HIGH)
        
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.availability_cache_ttl = availability_cache_ttl
        self._available: Optional[bool] = None
        self._unavailable_reason: Optional[str] = None
        self._last_availability_check: float = 0
        
        # 构建请求头
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def is_available(self) -> bool:
        """
        检查 Docling Serve 服务是否可用
        
        使用带过期时间的缓存，避免服务启动后一直返回不可用
        """
        current_time = time.time()
        
        # 如果缓存未过期且之前检查结果为可用，直接返回
        if self._available is True and (current_time - self._last_availability_check) < self.availability_cache_ttl:
            return True
        
        # 如果之前不可用，每次都重新检查（允许服务恢复）
        # 或者缓存已过期，也重新检查
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/health")
                self._available = response.status_code == 200
                self._last_availability_check = current_time
                if self._available:
                    self._unavailable_reason = None
                    logger.info(f"Docling Serve 服务可用: {self.base_url}")
                else:
                    self._unavailable_reason = f"Health check failed: HTTP {response.status_code}"
        except Exception as e:
            self._available = False
            self._last_availability_check = current_time
            self._unavailable_reason = f"Docling Serve 服务不可用: {e}"
            logger.warning(self._unavailable_reason)
        
        return self._available
    
    def get_unavailable_reason(self) -> Optional[str]:
        """返回不可用的原因"""
        self.is_available()  # 确保检查最新状态
        return self._unavailable_reason
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        同步解析文档
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict: 符合项目规范的解析结果
                - success: bool
                - loader: str
                - full_text: str
                - pages: List[Dict]
                - total_pages: int
                - total_chars: int
                - metadata: Dict
                - tables: List[Dict] (可选)
                - images: List[Dict] (可选)
                - error: str (失败时)
        """
        path = Path(file_path)
        
        # 验证文件
        if not path.exists():
            return {
                "success": False,
                "loader": self.name,
                "error": f"文件不存在: {file_path}"
            }
        
        file_format = path.suffix.lstrip('.').lower()
        if file_format not in self.SUPPORTED_FORMATS:
            return {
                "success": False,
                "loader": self.name,
                "error": f"不支持的文件格式: {path.suffix}"
            }
        
        # 读取文件并编码为 Base64
        try:
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return {
                "success": False,
                "loader": self.name,
                "error": f"读取文件失败: {e}"
            }
        
        # 构建请求体
        # Docling Serve API 格式参考: http://localhost:5001/docs
        request_body = {
            "options": {
                "to_formats": ["md"],
                "do_ocr": True,
                "force_ocr": True,  # 强制 OCR，对扫描件 PDF 必须
                "ocr_engine": "rapidocr",  # 使用 RapidOCR（支持中文）
                "ocr_lang": ["ch_sim", "en"],  # 简体中文+英文 OCR
                "table_mode": "accurate",
                "abort_on_error": False,
                "include_images": True,  # 提取图片
                "images_scale": 2.0,  # 图片缩放比例
                "image_export_mode": "embedded"  # 嵌入图片为 Base64
            },
            "sources": [
                {
                    "kind": "file",
                    "base64_string": file_content,
                    "filename": path.name
                }
            ]
        }
        
        # 发送请求（带重试）
        last_error = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/v1/convert/source",
                        headers=self.headers,
                        json=request_body
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return self._parse_response(result, path.name, file_format)
                    else:
                        last_error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}")
                        
            except httpx.TimeoutException:
                last_error = "请求超时"
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        return {
            "success": False,
            "loader": self.name,
            "error": f"文档解析失败: {last_error}"
        }
    
    def _parse_response(
        self,
        response: Dict[str, Any],
        filename: str,
        file_format: str
    ) -> Dict[str, Any]:
        """
        解析 Docling Serve 响应，转换为项目标准格式
        
        Args:
            response: API 响应
            filename: 原始文件名
            file_format: 文件格式
        
        Returns:
            Dict: 标准化的解析结果
        """
        try:
            # 获取文档结果
            documents = response.get("document", [])
            if not documents:
                documents = response.get("documents", [])
            
            if isinstance(documents, dict):
                documents = [documents]
            
            if not documents:
                return {
                    "success": False,
                    "loader": self.name,
                    "error": "响应中没有文档内容"
                }
            
            # 提取内容
            all_text_parts = []
            all_pages = []
            all_tables = []
            all_images = []
            total_pages = 0
            
            for doc in documents:
                # 提取 markdown 内容 (Docling Serve 使用 'md' 字段)
                md_content = (
                    doc.get('md', '') or
                    doc.get('md_content', '') or 
                    doc.get('markdown', '') or 
                    doc.get('content', '') or
                    doc.get('text', '')
                )
                
                if md_content:
                    all_text_parts.append(md_content)
                
                # 提取页面信息
                doc_pages = doc.get('pages', [])
                num_pages = doc.get('num_pages', 0) or len(doc_pages) or 1
                total_pages += num_pages
                
                if doc_pages:
                    for i, page_data in enumerate(doc_pages):
                        page_text = page_data.get('text', '') or page_data.get('content', '')
                        all_pages.append({
                            "page_number": page_data.get('page_number', i + 1),
                            "text": page_text,
                            "char_count": len(page_text)
                        })
                elif md_content:
                    # 如果没有分页信息，将整个内容作为一页
                    all_pages.append({
                        "page_number": 1,
                        "text": md_content,
                        "char_count": len(md_content)
                    })
                
                # 提取表格
                doc_tables = doc.get('tables', [])
                for i, table in enumerate(doc_tables):
                    all_tables.append({
                        "page_number": table.get('page_number', 1),
                        "table_index": i,
                        "headers": table.get('headers', []),
                        "rows": table.get('rows', []),
                        "caption": table.get('caption'),
                        "markdown": table.get('markdown', '')
                    })
                
                # 提取图片/图表
                doc_figures = doc.get('figures', []) or doc.get('images', [])
                for i, figure in enumerate(doc_figures):
                    all_images.append({
                        "page_number": figure.get('page_number', 1),
                        "image_index": i,
                        "caption": figure.get('caption'),
                        "alt_text": figure.get('alt_text'),
                        "bbox": figure.get('bbox')
                    })
            
            # 组合完整文本
            full_text = '\n\n'.join(all_text_parts)
            total_chars = len(full_text)
            
            # 如果没有页面但有文本，创建默认页面
            if not all_pages and full_text:
                all_pages = [{
                    "page_number": 1,
                    "text": full_text,
                    "char_count": total_chars
                }]
                total_pages = 1
            
            return {
                "success": True,
                "loader": self.name,
                "full_text": full_text,
                "pages": all_pages,
                "total_pages": total_pages or len(all_pages),
                "total_chars": total_chars,
                "tables": all_tables,
                "images": all_images,
                "metadata": {
                    "source": "docling_serve",
                    "filename": filename,
                    "format": file_format,
                    "table_count": len(all_tables),
                    "image_count": len(all_images)
                }
            }
            
        except Exception as e:
            logger.error(f"解析响应失败: {e}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": f"解析响应失败: {e}"
            }
    
    def reset_availability_cache(self):
        """重置可用性缓存，强制重新检查"""
        self._available = None
        self._unavailable_reason = None
    
    # ==================== 异步 API 方法 ====================
    
    def submit_async_convert(self, file_path: str) -> Dict[str, Any]:
        """
        提交异步转换任务
        
        使用 Docling Serve 的异步 API，立即返回 task_id，
        后续通过 poll_task_status 查询状态。
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict: {
                "success": bool,
                "task_id": str,  # Docling Serve 返回的任务 ID
                "status": str,   # pending/started
                "error": str     # 失败时的错误信息
            }
        """
        path = Path(file_path)
        
        # 验证文件
        if not path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        file_format = path.suffix.lstrip('.').lower()
        if file_format not in self.SUPPORTED_FORMATS:
            return {
                "success": False,
                "error": f"不支持的文件格式: {path.suffix}"
            }
        
        try:
            # 使用 multipart/form-data 上传文件
            with open(file_path, 'rb') as f:
                files = {"files": (path.name, f, self._get_mime_type(file_format))}
                data = {
                    "to_formats": "md",
                    "do_ocr": "true",
                    "force_ocr": "true",  # 强制 OCR，对扫描件 PDF 必须
                    "ocr_engine": "rapidocr",  # 使用 RapidOCR（支持中文）
                    "ocr_lang": "ch_sim,en",  # 简体中文+英文 OCR
                    "table_mode": "accurate",
                    "include_images": "true",  # 提取图片
                    "images_scale": "2.0",  # 图片缩放比例
                    "image_export_mode": "embedded"  # 嵌入图片为 Base64
                }
                
                with httpx.Client(timeout=30) as client:
                    response = client.post(
                        f"{self.base_url}/v1/convert/file/async",
                        files=files,
                        data=data,
                        headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                    )
                    
                    if response.status_code in (200, 202):
                        result = response.json()
                        task_id = result.get("task_id") or result.get("id")
                        task_status = result.get("task_status") or result.get("status", "pending")
                        
                        logger.info(f"异步任务已提交: task_id={task_id}, status={task_status}")
                        
                        return {
                            "success": True,
                            "task_id": task_id,
                            "status": task_status
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"提交异步任务失败: {error_msg}")
                        return {
                            "success": False,
                            "error": error_msg
                        }
                        
        except Exception as e:
            logger.error(f"提交异步任务异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def poll_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        轮询异步任务状态
        
        Args:
            task_id: Docling Serve 返回的任务 ID
        
        Returns:
            Dict: {
                "success": bool,
                "status": str,     # pending/started/success/failure
                "progress": int,   # 0-100 (如果支持)
                "error": str       # 失败时的错误信息
            }
        """
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.base_url}/v1/status/poll/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task_status = result.get("task_status") or result.get("status", "pending")
                    progress = result.get("progress", 0)
                    
                    # 映射状态
                    status_map = {
                        "pending": "pending",
                        "started": "started",
                        "running": "started",
                        "success": "success",
                        "completed": "success",
                        "failure": "failure",
                        "failed": "failure",
                        "error": "failure"
                    }
                    normalized_status = status_map.get(task_status.lower(), task_status)
                    
                    return {
                        "success": True,
                        "status": normalized_status,
                        "progress": progress,
                        "raw_response": result
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "status": "failure",
                        "error": f"任务不存在: {task_id}"
                    }
                else:
                    return {
                        "success": False,
                        "status": "failure",
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"轮询任务状态异常: {e}", exc_info=True)
            return {
                "success": False,
                "status": "failure",
                "error": str(e)
            }
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        获取异步任务结果
        
        任务完成后调用此方法获取解析结果。
        
        Args:
            task_id: Docling Serve 返回的任务 ID
        
        Returns:
            Dict: 符合项目规范的解析结果（与 extract_text 返回格式一致）
        """
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(
                    f"{self.base_url}/v1/result/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 复用现有的响应解析逻辑
                    return self._parse_response(result, f"task_{task_id}", "unknown")
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "loader": self.name,
                        "error": f"任务结果不存在: {task_id}"
                    }
                else:
                    return {
                        "success": False,
                        "loader": self.name,
                        "error": f"HTTP {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"获取任务结果异常: {e}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": str(e)
            }
    
    def _get_mime_type(self, file_format: str) -> str:
        """获取文件 MIME 类型"""
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xls': 'application/vnd.ms-excel',
            'html': 'text/html',
            'htm': 'text/html',
            'md': 'text/markdown',
            'txt': 'text/plain',
            'csv': 'text/csv',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
            'bmp': 'image/bmp',
            'gif': 'image/gif'
        }
        return mime_types.get(file_format, 'application/octet-stream')


def _create_docling_serve_loader() -> Optional[DoclingServeLoader]:
    """
    从环境变量创建 Docling Serve Loader
    
    环境变量:
        DOCLING_SERVE_URL: 服务地址 (默认: http://localhost:5001)
        DOCLING_SERVE_API_KEY: API 密钥 (可选)
        DOCLING_SERVE_TIMEOUT: 超时时间 (默认: 300)
        DOCLING_SERVE_ENABLED: 是否启用 (默认: true)
    
    Returns:
        DoclingServeLoader 实例
    """
    enabled = os.getenv('DOCLING_SERVE_ENABLED', 'true').lower() == 'true'
    
    if not enabled:
        logger.info("Docling Serve 已在配置中禁用")
        return None
    
    base_url = os.getenv('DOCLING_SERVE_URL', 'http://localhost:5001')
    api_key = os.getenv('DOCLING_SERVE_API_KEY', '')
    timeout = int(os.getenv('DOCLING_SERVE_TIMEOUT', '300'))
    
    loader = DoclingServeLoader(
        base_url=base_url,
        api_key=api_key if api_key else None,
        timeout=timeout
    )
    
    logger.info(f"Docling Serve Loader 已创建: {base_url}")
    return loader


# 创建全局实例
docling_serve_loader = _create_docling_serve_loader()
