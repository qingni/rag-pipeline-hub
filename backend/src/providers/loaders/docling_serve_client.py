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
from ...utils.image_storage import get_image_storage_manager, ImageStorageManager

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
        检查 Docling Serve 服务是否可用（同步版本，仅返回缓存值）
        
        注意：此方法不再发起 HTTP 请求，仅返回缓存的可用性状态。
        如需实时检查，请使用 is_available_async()。
        """
        # 直接返回缓存的可用性状态，避免阻塞事件循环
        if self._available is not None:
            return self._available
        # 首次调用时返回 False，等待异步检查
        return False
    
    async def is_available_async(self) -> bool:
        """
        异步检查 Docling Serve 服务是否可用
        
        使用带过期时间的缓存，避免服务启动后一直返回不可用。
        此方法使用异步 HTTP 客户端，不会阻塞事件循环。
        """
        current_time = time.time()
        
        # 如果缓存未过期且之前检查结果为可用，直接返回
        if self._available is True and (current_time - self._last_availability_check) < self.availability_cache_ttl:
            return True
        
        # 如果之前不可用，每次都重新检查（允许服务恢复）
        # 或者缓存已过期，也重新检查
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:  # 使用异步客户端，缩短超时
                response = await client.get(f"{self.base_url}/health")
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
        """返回不可用的原因（仅返回缓存值，不发起检查）"""
        return self._unavailable_reason
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """
        解析文档（仅提交异步任务，不内部轮询）
        
        重要变更：此方法不再内部轮询等待结果，而是提交任务后立即返回。
        对于需要获取结果的场景，应使用异步加载流程：
        1. submit_async_convert() 提交任务
        2. poll_task_status_async() 异步轮询状态
        3. get_task_result_async() 异步获取结果
        
        此同步方法仅用于兼容旧的调用方式，但会标记为 async_mode=True，
        让上层调用者知道需要通过异步流程完成处理。
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict: 包含 async_mode=True 和 task_id 的结果，
                  上层应通过异步流程继续处理
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
        
        # 提交异步任务
        logger.info(f"[Docling] 提交异步任务: {path.name}")
        submit_result = self.submit_async_convert(file_path)
        
        if not submit_result.get("success"):
            return {
                "success": False,
                "loader": self.name,
                "error": submit_result.get("error", "提交异步任务失败")
            }
        
        task_id = submit_result.get("task_id")
        if not task_id:
            return {
                "success": False,
                "loader": self.name,
                "error": "未获取到任务 ID"
            }
        
        # 返回异步任务信息，不再内部轮询
        # 上层调用者应通过异步流程获取结果
        logger.info(f"[Docling] 异步任务已提交: task_id={task_id}, file={path.name}")
        
        return {
            "success": True,
            "async_mode": True,  # 标记为异步模式，上层需要继续处理
            "task_id": task_id,
            "status": "pending",
            "loader": self.name,
            "file_path": file_path,
            "file_format": file_format,
            "filename": path.name
        }
    
    def _extract_sheet_info(self, doc: Dict[str, Any], md_content: str) -> Tuple[List[str], int]:
        """
        从 Docling 响应中提取 Excel Sheet 信息
        
        Docling 将 Excel 的每个 Sheet 作为一个 Group，
        Group.name 格式为 "sheet: {sheet_name}"
        
        当请求 to_formats 包含 "json" 时，响应中的 json_content 字段包含结构化数据
        
        Args:
            doc: Docling 响应中的文档对象
            md_content: Markdown 内容
        
        Returns:
            Tuple[List[str], int]: (sheet_names 列表, sheet_count)
        """
        import re
        sheet_names = []
        
        # 方法1：从 json_content 字段的结构化数据中提取（优先）
        # Docling Serve 返回的字段是 json_content 而不是 json
        json_data = doc.get('json_content', {}) or doc.get('json', {})
        if isinstance(json_data, str):
            # 如果是字符串，尝试解析
            import json
            try:
                json_data = json.loads(json_data)
            except:
                json_data = {}
        
        if json_data:
            # Docling JSON 结构中的 groups 包含 Sheet 信息
            # 格式: {"groups": [{"name": "sheet: 2023年10大首富", ...}, ...]}
            groups = json_data.get('groups', [])
            for group in groups:
                group_name = group.get('name', '') or group.get('label', '')
                # Docling 格式: "sheet: Sheet1" 或 "sheet: 2023年10大首富"
                if group_name.lower().startswith('sheet:'):
                    sheet_name = group_name[6:].strip()
                    if sheet_name and sheet_name not in sheet_names:
                        sheet_names.append(sheet_name)
            
            # 检查 furniture 中是否有 sheet 信息
            furniture = json_data.get('furniture', {})
            if furniture and not sheet_names:
                items = furniture.get('children', []) or furniture.get('items', [])
                for item in items:
                    if isinstance(item, dict):
                        item_label = item.get('label', '')
                        item_text = item.get('text', '') or item.get('name', '')
                        if 'sheet' in item_label.lower():
                            if item_text and item_text not in sheet_names:
                                sheet_names.append(item_text)
        
        # 方法2：从顶层 groups 结构中提取（某些 Docling 版本）
        if not sheet_names:
            groups = doc.get('groups', []) or doc.get('body', {}).get('groups', [])
            for group in groups:
                group_name = group.get('name', '') or group.get('label', '')
                if group_name.lower().startswith('sheet:'):
                    sheet_name = group_name[6:].strip()
                    if sheet_name and sheet_name not in sheet_names:
                        sheet_names.append(sheet_name)
        
        # 方法3：从 Markdown 内容中解析 Sheet 标题
        # Docling 在 Markdown 中可能生成 "## Sheet: {name}" 格式的标题
        if not sheet_names and md_content:
            sheet_pattern = re.compile(r'^##\s+[Ss]heet:\s*(.+)$', re.MULTILINE)
            matches = sheet_pattern.findall(md_content)
            for match in matches:
                sheet_name = match.strip()
                if sheet_name and sheet_name not in sheet_names:
                    sheet_names.append(sheet_name)
        
        # 方法4：从 sections/items 中提取
        if not sheet_names:
            sections = doc.get('sections', []) or doc.get('items', [])
            for section in sections:
                section_type = section.get('type', '') or section.get('label', '')
                section_name = section.get('name', '') or section.get('title', '')
                if 'sheet' in section_type.lower() or section_name.lower().startswith('sheet:'):
                    name = section_name[6:].strip() if section_name.lower().startswith('sheet:') else section_name
                    if name and name not in sheet_names:
                        sheet_names.append(name)
        
        sheet_count = len(sheet_names) if sheet_names else 0
        
        # 调试日志
        if sheet_names:
            logger.info(f"[Excel] 提取到 {sheet_count} 个 Sheet: {sheet_names}")
        else:
            logger.warning(f"[Excel] 未能提取 Sheet 信息，doc keys: {list(doc.keys())}")
        
        return sheet_names, sheet_count

    def _split_excel_by_sheets(self, full_text: str, sheet_names: List[str]) -> List[Dict[str, Any]]:
        """
        将 Excel 的 markdown 内容按 sheet 分割成多个 pages
        
        Docling 生成的 markdown 中，每个表格对应一个 sheet，
        表格之间以空行分隔。我们按表格数量与 sheet 数量对应来分割。
        
        Args:
            full_text: 完整的 markdown 文本
            sheet_names: sheet 名称列表
        
        Returns:
            List[Dict]: 按 sheet 分割的 pages 列表
        """
        import re
        pages = []
        
        # 策略1: 尝试按 markdown 表格分割
        # Docling 生成的表格格式: |...|...|... 每行以 | 开头
        # 表格之间有空行分隔
        
        # 用正则匹配完整的 markdown 表格块
        # 匹配连续的以 | 开头的行（包括表头、分隔行、数据行）
        table_pattern = re.compile(r'(\|[^\n]+\n(?:\|[^\n]+\n)*)', re.MULTILINE)
        tables = table_pattern.findall(full_text)
        
        if len(tables) == len(sheet_names):
            # 表格数量与 sheet 数量匹配，一一对应
            for i, (table_content, sheet_name) in enumerate(zip(tables, sheet_names)):
                pages.append({
                    "page_number": i + 1,
                    "text": table_content.strip(),
                    "char_count": len(table_content),
                    "sheet_name": sheet_name
                })
            logger.info(f"[Excel] 按表格分割成功，共 {len(pages)} 个 sheet")
        else:
            # 数量不匹配，尝试按空行分割
            # 多个连续空行作为分隔符
            sections = re.split(r'\n\s*\n\s*\n', full_text)
            sections = [s.strip() for s in sections if s.strip()]
            
            if len(sections) == len(sheet_names):
                for i, (section, sheet_name) in enumerate(zip(sections, sheet_names)):
                    pages.append({
                        "page_number": i + 1,
                        "text": section,
                        "char_count": len(section),
                        "sheet_name": sheet_name
                    })
                logger.info(f"[Excel] 按空行分割成功，共 {len(pages)} 个 sheet")
            else:
                # 无法精确分割，尝试均匀分割文本
                logger.warning(f"[Excel] 表格数({len(tables)})与sheet数({len(sheet_names)})不匹配，使用均匀分割")
                
                # 按双空行分割，然后合并
                parts = re.split(r'\n\n+', full_text)
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= len(sheet_names):
                    # 将 parts 均匀分配到各 sheet
                    parts_per_sheet = len(parts) // len(sheet_names)
                    remainder = len(parts) % len(sheet_names)
                    
                    idx = 0
                    for i, sheet_name in enumerate(sheet_names):
                        # 前 remainder 个 sheet 多分配一个 part
                        count = parts_per_sheet + (1 if i < remainder else 0)
                        sheet_parts = parts[idx:idx + count]
                        idx += count
                        
                        text = '\n\n'.join(sheet_parts)
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                            "char_count": len(text),
                            "sheet_name": sheet_name
                        })
                else:
                    # parts 数量不足，每个 sheet 分配一个（可能有空的）
                    for i, sheet_name in enumerate(sheet_names):
                        text = parts[i] if i < len(parts) else ""
                        pages.append({
                            "page_number": i + 1,
                            "text": text,
                            "char_count": len(text),
                            "sheet_name": sheet_name
                        })
        
        return pages

    def _parse_response(
        self,
        response: Dict[str, Any],
        filename: str,
        file_format: str,
        figures_dir: Optional[Path] = None
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
            # 调试日志：打印响应结构的顶层 keys
            logger.info(f"[DEBUG] _parse_response called: filename={filename}, format={file_format}, response_keys={list(response.keys())}")
            
            # 获取文档结果
            documents = response.get("document", [])
            if not documents:
                documents = response.get("documents", [])
            
            logger.info(f"[DEBUG] documents type={type(documents).__name__}, is_empty={not documents}")
            
            if isinstance(documents, dict):
                documents = [documents]
            
            logger.info(f"[DEBUG] After conversion: documents count={len(documents)}, first doc keys={list(documents[0].keys()) if documents else 'N/A'}")
            
            if not documents:
                # 检查是否有错误详情
                detail = response.get("detail", "")
                logger.error(f"[Docling] 响应中没有文档内容: filename={filename}, detail={detail}, keys={list(response.keys())}")
                return {
                    "success": False,
                    "loader": self.name,
                    "error": f"响应中没有文档内容: {detail}" if detail else "响应中没有文档内容"
                }
            
            # 调试日志：打印文档对象的 keys（仅对 Excel 文件）
            if file_format in ('xlsx', 'xls') and documents:
                logger.info(f"[Excel Debug] Document keys: {list(documents[0].keys())}")
                # 如果有 json_content 字段，打印其结构
                json_data = documents[0].get('json_content') or documents[0].get('json')
                if json_data and isinstance(json_data, dict):
                    logger.info(f"[Excel Debug] JSON content keys: {list(json_data.keys())}")
                    # 打印 groups 信息
                    groups = json_data.get('groups', [])
                    if groups:
                        logger.info(f"[Excel Debug] Groups count: {len(groups)}")
                        for i, g in enumerate(groups[:3]):
                            logger.info(f"[Excel Debug] Group[{i}] name: {g.get('name', 'N/A')}")
            
            # 提取内容
            all_text_parts = []
            all_pages = []
            all_tables = []
            all_images = []
            total_pages = 0
            all_sheet_names = []  # Excel sheet 名称汇总
            
            for doc in documents:
                # 提取 markdown 内容 (Docling Serve 使用 'md_content' 字段)
                md_content = (
                    doc.get('md_content', '') or
                    doc.get('md', '') or
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
                
                # 提取图片/图表 (增强多模态支持)
                doc_figures = doc.get('figures', []) or doc.get('images', [])
                for i, figure in enumerate(doc_figures):
                    image_info = {
                        "page_number": figure.get('page_number', 1),
                        "image_index": i,
                        "caption": figure.get('caption'),
                        "alt_text": figure.get('alt_text'),
                        "bbox": figure.get('bbox'),
                        # 多模态支持字段
                        "file_path": figure.get('file_path'),
                        "base64_data": figure.get('base64') or figure.get('image_base64'),
                        "mime_type": figure.get('mime_type', 'image/png'),
                        "width": figure.get('width'),
                        "height": figure.get('height'),
                        "context_before": figure.get('context_before'),
                        "context_after": figure.get('context_after'),
                        "image_type": figure.get('type', 'figure'),
                        "ocr_text": figure.get('ocr_text')
                    }
                    all_images.append(image_info)
                
                # 仅对 Excel 格式提取 sheet 信息
                if file_format in ('xlsx', 'xls'):
                    sheet_names, _ = self._extract_sheet_info(doc, md_content)
                    for name in sheet_names:
                        if name not in all_sheet_names:
                            all_sheet_names.append(name)
            
            # 组合完整文本
            full_text = '\n\n'.join(all_text_parts)
            logger.info(f"[DEBUG] After text extraction: full_text length={len(full_text)}, pages={len(all_pages)}, tables={len(all_tables)}, images={len(all_images)}")
            
            # 从 Markdown 中提取图片信息（如果 Docling API 没有返回 figures）
            if not all_images:
                logger.info(f"[DEBUG] Extracting images from markdown (text length={len(full_text)})...")
                all_images = self._extract_images_from_markdown(full_text, figures_dir)
                logger.info(f"[DEBUG] Image extraction done, found {len(all_images)} images")
                if all_images:
                    logger.info(f"从 Markdown 中提取到 {len(all_images)} 张图片")
            
            # 关键：将内联 base64 图片转换为占位符格式
            # 目的：避免超长 base64 字符串干扰语义分块和消耗 token
            if all_images:
                logger.info(f"[DEBUG] Converting inline images to placeholders...")
                original_len = len(full_text)
                full_text = self._convert_inline_images_to_placeholders(full_text, all_images)
                reduced_chars = original_len - len(full_text)
                logger.info(f"[DEBUG] Placeholder conversion done")
                if reduced_chars > 0:
                    logger.info(f"[图片占位符转换] 减少 {reduced_chars} 字符 ({reduced_chars / original_len * 100:.1f}%)")
            
            logger.info(f"[DEBUG] Building result structure...")
            
            total_chars = len(full_text)
            
            # 对 HTML 格式，生成 RAG 友好的结构化文本
            if file_format in ('html', 'htm'):
                structured_text = self._generate_html_structured_text(full_text, all_images)
            else:
                structured_text = None
            
            # 对 Excel 文件，按 sheet 分割内容到不同的 pages
            if file_format in ('xlsx', 'xls') and all_sheet_names and full_text:
                all_pages = self._split_excel_by_sheets(full_text, all_sheet_names)
                total_pages = len(all_pages)
            # 如果没有页面但有文本，创建默认页面
            elif not all_pages and full_text:
                all_pages = [{
                    "page_number": 1,
                    "text": full_text,
                    "char_count": total_chars
                }]
                total_pages = 1
            # 对已有的 pages 也进行占位符转换
            elif all_pages and all_images:
                for page in all_pages:
                    if page.get("text"):
                        page["text"] = self._convert_inline_images_to_placeholders(
                            page["text"], all_images
                        )
                        page["char_count"] = len(page["text"])
            
            # 构建基础元数据
            metadata = {
                "source": "docling_serve",
                "filename": filename,
                "format": file_format,
                "table_count": len(all_tables),
                "image_count": len(all_images),
                "has_images": len(all_images) > 0
            }
            
            # 仅对 Excel 格式添加 sheet 元数据
            if file_format in ('xlsx', 'xls') and all_sheet_names:
                metadata["sheet_count"] = len(all_sheet_names)
                metadata["sheet_names"] = all_sheet_names
            
            result = {
                "success": True,
                "loader": self.name,
                "full_text": full_text,
                "pages": all_pages,
                "total_pages": total_pages or len(all_pages),
                "total_chars": total_chars,
                "tables": all_tables,
                "images": all_images,
                "metadata": metadata
            }
            
            # 对 HTML 格式添加结构化文本
            if structured_text:
                result["structured_text"] = structured_text
            
            logger.info(f"[DEBUG] _parse_response completed successfully: total_pages={result['total_pages']}, total_chars={result['total_chars']}")
            return result
            
        except Exception as e:
            logger.error(f"解析响应失败: {e}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": f"解析响应失败: {e}"
            }
    
    def _extract_images_from_markdown(
        self, 
        md_content: str,
        figures_dir: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        从 Markdown 内容中提取图片信息（高性能优化版本）
        
        业内最佳实践：
        1. 使用字符串查找替代正则（避免超长 base64 的正则性能问题）
        2. 大图保存为文件，小图保留 base64（混合存储策略）
        3. 生成缩略图用于预览
        
        Args:
            md_content: Markdown 文本内容
            figures_dir: 图片保存目录（可选，用于大图存储）
        
        Returns:
            List[Dict]: 图片信息列表
        """
        images = []
        
        # 使用公共图片存储管理器
        storage_manager = get_image_storage_manager()
        
        # 使用字符串查找，避免正则性能问题
        search_pos = 0
        img_index = 0
        
        while True:
            # 查找 ![
            img_start = md_content.find('![', search_pos)
            if img_start == -1:
                break
            
            # 查找 ](
            bracket_pos = md_content.find('](', img_start)
            if bracket_pos == -1 or bracket_pos > img_start + 500:  # alt 文本限制 500 字符
                search_pos = img_start + 2
                continue
            
            # 提取 alt 文本
            alt_text = md_content[img_start + 2:bracket_pos]
            
            # 查找结束的 )，需要处理嵌套括号
            paren_count = 1
            end_pos = bracket_pos + 2
            while end_pos < len(md_content) and paren_count > 0:
                if md_content[end_pos] == '(':
                    paren_count += 1
                elif md_content[end_pos] == ')':
                    paren_count -= 1
                end_pos += 1
            
            if paren_count != 0:
                search_pos = bracket_pos + 2
                continue
            
            # 提取 src
            src = md_content[bracket_pos + 2:end_pos - 1]
            
            # 判断是否为 base64 图片
            is_base64 = src.startswith('data:image/')
            
            # 获取图片上下文（前后各 100 字符）
            context_before = md_content[max(0, img_start - 100):img_start].strip()
            context_after = md_content[end_pos:min(len(md_content), end_pos + 100)].strip()
            context_before = ' '.join(context_before.split())
            context_after = ' '.join(context_after.split())
            
            image_info = {
                "page_number": 1,
                "image_index": img_index,
                "alt_text": alt_text or f'图片{img_index + 1}',
                "is_base64": is_base64,
                "extracted_from": "markdown",
                "context_before": context_before if context_before else None,
                "context_after": context_after if context_after else None,
            }
            
            if is_base64:
                # 解析 base64 数据
                try:
                    # 分离 mime type 和数据
                    if ',' in src:
                        header, raw_base64_data = src.split(',', 1)
                    else:
                        header, raw_base64_data = '', src
                    
                    mime_type = header.split(';')[0].replace('data:', '') if header else 'image/png'
                    
                    # 使用公共存储策略处理图片
                    storage_result = storage_manager.process_base64_image(
                        base64_data=raw_base64_data,
                        image_index=img_index,
                        figures_dir=figures_dir,
                        page_number=1,
                        mime_type=mime_type,
                    )
                    
                    # 合并存储结果到 image_info
                    image_info["mime_type"] = storage_result["mime_type"]
                    image_info["original_size"] = storage_result["original_size"]
                    image_info["file_path"] = storage_result["file_path"]
                    image_info["base64_data"] = storage_result["base64_data"]
                    image_info["thumbnail_base64"] = storage_result.get("thumbnail_base64")
                    image_info["width"] = storage_result["width"]
                    image_info["height"] = storage_result["height"]
                    
                    if storage_result.get("error"):
                        image_info["error"] = storage_result["error"]
                        
                except Exception as e:
                    logger.warning(f"处理 base64 图片失败: {e}")
                    image_info["error"] = str(e)
                    image_info["base64_data"] = None
            else:
                # 普通 URL 图片
                image_info["src"] = src
                image_info["file_path"] = None
                image_info["base64_data"] = None
                image_info["mime_type"] = self._detect_image_mime_type(src)
            
            images.append(image_info)
            img_index += 1
            search_pos = end_pos
        
        # 匹配 Docling 的图片占位符注释: <!-- 🖼️❌ Image not available ... -->
        placeholder_search_pos = 0
        placeholder_marker = '<!-- 🖼️❌ Image not available'
        
        while True:
            marker_pos = md_content.find(placeholder_marker, placeholder_search_pos)
            if marker_pos == -1:
                break
            
            # 找到注释结束位置
            end_marker = md_content.find('-->', marker_pos)
            if end_marker == -1:
                placeholder_search_pos = marker_pos + len(placeholder_marker)
                continue
            
            end_pos = end_marker + 3
            
            # 获取占位符前面的文本作为 alt_text
            line_start = md_content.rfind('\n', 0, marker_pos)
            line_start = line_start + 1 if line_start != -1 else 0
            preceding_text = md_content[line_start:marker_pos].strip()
            
            # 获取上下文
            context_before = md_content[max(0, line_start - 150):line_start].strip()
            context_after = md_content[end_pos:min(len(md_content), end_pos + 150)].strip()
            context_before = ' '.join(context_before.split())
            context_after = ' '.join(context_after.split())
            
            image_info = {
                "page_number": 1,
                "image_index": img_index,
                "src": None,
                "alt_text": preceding_text if preceding_text else f'图片{img_index + 1}',
                "caption": preceding_text,
                "mime_type": None,
                "is_base64": False,
                "extracted_from": "docling_placeholder",
                "context_before": context_before if context_before else None,
                "context_after": context_after if context_after else None
            }
            
            images.append(image_info)
            img_index += 1
            placeholder_search_pos = end_pos
        
        if images:
            logger.info(f"[图片提取] 共提取 {len(images)} 张图片")
        
        return images
    
    def _convert_inline_images_to_placeholders(
        self,
        md_content: str,
        images: List[Dict[str, Any]]
    ) -> str:
        """
        将 Markdown 中的内联图片转换为占位符格式（高性能优化版本）
        
        目的：
        1. 避免超长 base64 字符串干扰语义分块
        2. 减少 token 消耗
        3. 保持文本语义连贯性
        
        转换示例：
        原: ![Image](data:image/png;base64,iVBORw0KGgo...)
        改: [IMAGE_1: Image]
        
        Args:
            md_content: 原始 Markdown 内容
            images: 已提取的图片信息列表
        
        Returns:
            str: 转换后的文本（图片位置用占位符替代）
        """
        if not images:
            return md_content
        
        result = md_content
        replacements = []  # (start, end, placeholder, alt_text)
        
        # 使用字符串查找替代正则，避免性能问题
        search_pos = 0
        img_idx = 0
        
        while True:
            # 查找 ![
            img_start = result.find('![', search_pos)
            if img_start == -1:
                break
            
            # 查找 ](
            bracket_pos = result.find('](', img_start)
            if bracket_pos == -1 or bracket_pos > img_start + 500:
                search_pos = img_start + 2
                continue
            
            # 提取 alt 文本
            alt_text = result[img_start + 2:bracket_pos]
            
            # 查找结束的 )，处理嵌套括号
            paren_count = 1
            end_pos = bracket_pos + 2
            while end_pos < len(result) and paren_count > 0:
                if result[end_pos] == '(':
                    paren_count += 1
                elif result[end_pos] == ')':
                    paren_count -= 1
                end_pos += 1
            
            if paren_count != 0:
                search_pos = bracket_pos + 2
                continue
            
            img_idx += 1
            placeholder = f"[IMAGE_{img_idx}: {alt_text or '图片'}]"
            replacements.append((img_start, end_pos, placeholder))
            search_pos = end_pos
        
        # 处理 Docling 的无效图片占位符: <!-- 🖼️❌ Image not available ... -->
        placeholder_marker = '<!-- 🖼️❌ Image not available'
        placeholder_search_pos = 0
        
        while True:
            marker_pos = result.find(placeholder_marker, placeholder_search_pos)
            if marker_pos == -1:
                break
            
            end_marker = result.find('-->', marker_pos)
            if end_marker == -1:
                placeholder_search_pos = marker_pos + len(placeholder_marker)
                continue
            
            end_pos = end_marker + 3
            
            # 获取前面一行的文本作为 alt
            line_start = result.rfind('\n', 0, marker_pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            
            preceding_text = result[line_start:marker_pos].strip()
            
            img_idx += 1
            placeholder = f"[IMAGE_{img_idx}: {preceding_text or '图片'}]"
            
            # 替换整行（包括前面的文本）
            replacements.append((line_start, end_pos, placeholder))
            placeholder_search_pos = end_pos
        
        # 从后往前替换（避免位置偏移）
        replacements.sort(key=lambda x: x[0], reverse=True)
        for start, end, placeholder in replacements:
            result = result[:start] + placeholder + result[end:]
        
        return result

    def _detect_image_mime_type(self, src: str) -> Optional[str]:
        """检测图片的 MIME 类型"""
        if not src:
            return None
        
        # base64 图片
        if src.startswith('data:'):
            try:
                header = src.split(',')[0]
                if ';' in header:
                    return header.split(':')[1].split(';')[0]
            except (IndexError, ValueError):
                pass
            return 'image/png'
        
        # 根据扩展名判断
        src_lower = src.lower().split('?')[0]
        
        extension_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.bmp': 'image/bmp',
            '.avif': 'image/avif'
        }
        
        for ext, mime in extension_map.items():
            if src_lower.endswith(ext):
                return mime
        
        return None
    
    def _generate_html_structured_text(self, md_content: str, images: List[Dict[str, Any]]) -> str:
        """
        生成 RAG 友好的结构化文本，在图片位置插入详细标记
        
        Args:
            md_content: Markdown 文本内容
            images: 提取的图片信息列表
        
        Returns:
            str: 带有图片标记的结构化文本
        """
        import re
        
        if not images:
            return md_content
        
        result = md_content
        
        # 1. 处理标准 Markdown 图片语法: ![alt](src)
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
        matches = list(img_pattern.finditer(md_content))
        
        # 按位置从后往前替换，避免位置偏移
        for idx, match in enumerate(reversed(matches)):
            img_idx = len(matches) - 1 - idx
            img_info = self._find_image_by_index(images, img_idx, 'markdown')
            if img_info:
                marker = self._build_image_marker(img_info)
                result = result[:match.start()] + marker + result[match.end():]
        
        # 2. 处理 Docling 占位符: <!-- 🖼️❌ Image not available ... -->
        # 同时包含前面的 alt_text 行
        placeholder_pattern = re.compile(
            r'([^\n]*)\n*<!-- 🖼️❌ Image not available[^>]*-->',
            re.MULTILINE
        )
        placeholder_matches = list(placeholder_pattern.finditer(result))
        
        # 按位置从后往前替换
        for idx, match in enumerate(reversed(placeholder_matches)):
            # 查找对应的图片信息
            img_info = self._find_image_by_index(images, len(placeholder_matches) - 1 - idx, 'docling_placeholder')
            if img_info:
                marker = self._build_image_marker(img_info)
                result = result[:match.start()] + marker + result[match.end():]
        
        return result
    
    def _find_image_by_index(self, images: List[Dict[str, Any]], idx: int, source: str) -> Optional[Dict[str, Any]]:
        """根据索引和来源查找图片信息"""
        # 先尝试按索引匹配
        for img in images:
            if img.get('image_index') == idx:
                # 检查来源是否匹配
                img_source = img.get('extracted_from', 'markdown')
                if source == 'docling_placeholder' and img_source == 'docling_placeholder':
                    return img
                elif source == 'markdown' and img_source != 'docling_placeholder':
                    return img
        
        # 如果没找到完全匹配的，按索引返回
        if idx < len(images):
            return images[idx]
        
        return None
    
    def _build_image_marker(self, img_info: Dict[str, Any]) -> str:
        """构建图片标记字符串"""
        idx = img_info.get('image_index', 0)
        src = img_info.get('src', '')
        alt = img_info.get('alt_text', '')
        caption = img_info.get('caption', '')
        context = img_info.get('context', {})
        
        detail_parts = []
        
        if src:
            detail_parts.append(f'src="{src}"')
        if alt:
            detail_parts.append(f'alt="{alt}"')
        if caption and caption != alt:
            detail_parts.append(f'caption="{caption}"')
        
        # 添加上下文提示
        ctx_hints = []
        if context and context.get('text_before'):
            ctx_hints.append(f"前文: {context['text_before'][:50]}")
        if context and context.get('text_after'):
            ctx_hints.append(f"后文: {context['text_after'][:50]}")
        if ctx_hints:
            detail_parts.append(f'context="{"; ".join(ctx_hints)}"')
        
        # 占位符索引从1开始（人类可读），images数组的image_index从0开始
        placeholder_idx = idx + 1
        if detail_parts:
            return f"\n[IMAGE_{placeholder_idx}] ({' '.join(detail_parts)})\n"
        else:
            return f"\n[IMAGE_{placeholder_idx}]\n"
    
    def reset_availability_cache(self):
        """重置可用性缓存，强制重新检查"""
        self._available = None
        self._unavailable_reason = None
    
    # ==================== 异步 API 方法 ====================
    
    async def poll_task_status_async(self, task_id: str) -> Dict[str, Any]:
        """
        异步轮询任务状态（使用 httpx.AsyncClient，不阻塞事件循环）
        
        此方法是核心的异步实现，避免阻塞 FastAPI 事件循环。
        
        Args:
            task_id: Docling Serve 返回的任务 ID
        
        Returns:
            Dict: {
                "success": bool,
                "status": str,     # pending/started/success/failure
                "progress": int,   # 0-100
                "error": str       # 失败时的错误信息
            }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = await client.get(
                    f"{self.base_url}/v1/status/poll/{task_id}",
                    headers=headers
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
                    
                    # 如果任务成功但没有进度信息，设为 100%
                    if normalized_status == "success" and progress == 0:
                        progress = 100
                    
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
                    
        except httpx.TimeoutException:
            logger.warning(f"[Docling] 异步轮询超时: task_id={task_id}")
            return {
                "success": False,
                "error": "请求超时"
            }
        except Exception as e:
            logger.error(f"[Docling] 异步轮询异常: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_task_result_async(
        self,
        task_id: str,
        filename: Optional[str] = None,
        file_format: Optional[str] = None,
        max_retries: int = 5,
        retry_delay: float = 1.0,
        figures_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        异步获取任务结果（使用 httpx.AsyncClient，不阻塞事件循环）
        
        任务完成后调用此方法获取解析结果。包含重试机制以处理结果写入延迟。
        
        Args:
            task_id: Docling Serve 返回的任务 ID
            filename: 原始文件名（用于元数据）
            file_format: 文件格式（如 xlsx、pdf 等）
            max_retries: 最大重试次数（默认 5 次）
            retry_delay: 重试间隔秒数（默认 1 秒）
        
        Returns:
            Dict: 符合项目规范的解析结果
        """
        import asyncio
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[DEBUG] get_task_result_async attempt {attempt + 1}/{max_retries} for task_id={task_id}")
                timeout_config = httpx.Timeout(
                    connect=10.0,
                    read=float(self.timeout),
                    write=float(self.timeout),
                    pool=float(self.timeout)
                )
                async with httpx.AsyncClient(timeout=timeout_config) as client:
                    headers = {}
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    response = await client.get(
                        f"{self.base_url}/v1/result/{task_id}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info(f"[DEBUG] Got response 200, result keys: {list(result.keys())[:10]}")
                        
                        # 检查是否真的有结果（处理竞态条件）
                        if "detail" in result and "document" not in result:
                            detail_msg = result.get("detail", "")
                            if "not found" in detail_msg.lower() or "wait" in detail_msg.lower():
                                # 结果还没准备好，重试
                                if attempt < max_retries - 1:
                                    logger.info(f"[Docling] 结果未就绪，等待重试 ({attempt + 1}/{max_retries}): {detail_msg}")
                                    await asyncio.sleep(retry_delay)
                                    continue
                                else:
                                    logger.warning(f"[Docling] 重试 {max_retries} 次后结果仍未就绪: {detail_msg}")
                                    return {
                                        "success": False,
                                        "loader": self.name,
                                        "error": f"结果获取超时: {detail_msg}"
                                    }
                        
                        # 复用现有的响应解析逻辑
                        actual_filename = filename or f"task_{task_id}"
                        actual_format = file_format or "unknown"
                        logger.info(f"[DEBUG] Calling _parse_response for {actual_filename}, format={actual_format}, figures_dir={figures_dir}")
                        parse_result = self._parse_response(result, actual_filename, actual_format, figures_dir)
                        logger.info(f"[DEBUG] _parse_response returned: success={parse_result.get('success')}, error={parse_result.get('error')}")
                        return parse_result
                    elif response.status_code == 404:
                        # 404 也可能是暂时的，重试
                        if attempt < max_retries - 1:
                            logger.info(f"[Docling] 结果 404，等待重试 ({attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
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
                        
            except httpx.TimeoutException:
                logger.warning(f"[Docling] 获取结果超时: task_id={task_id}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return {
                    "success": False,
                    "loader": self.name,
                    "error": "获取结果超时"
                }
            except Exception as e:
                logger.error(f"[Docling] 获取结果异常: {e}", exc_info=True)
                return {
                    "success": False,
                    "loader": self.name,
                    "error": str(e)
                }
        
        # 不应该到达这里，但作为安全措施
        return {
            "success": False,
            "loader": self.name,
            "error": f"获取结果失败，重试 {max_retries} 次"
        }

    def submit_async_convert(self, file_path: str) -> Dict[str, Any]:
        """
        提交异步转换任务（同步版本，仅用于兼容）
        
        注意：此同步方法会在 ThreadPoolExecutor 中调用，可能阻塞线程池。
        推荐使用 submit_async_convert_async() 异步版本。
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict: {
                "success": bool,
                "task_id": str,
                "status": str,
                "error": str
            }
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        file_format = path.suffix.lstrip('.').lower()
        if file_format not in self.SUPPORTED_FORMATS:
            return {"success": False, "error": f"不支持的文件格式: {path.suffix}"}
        
        try:
            is_excel = file_format in ('xlsx', 'xls')
            
            with open(file_path, 'rb') as f:
                files = {"files": (path.name, f, self._get_mime_type(file_format))}
                data = {
                    "do_ocr": "true",
                    "force_ocr": "true",  # 强制 OCR，确保扫描件/图片PDF被正确识别
                    "ocr_engine": "rapidocr",
                    "ocr_lang": "ch_sim,en",
                    "table_mode": "accurate",
                    "include_images": "true",
                    "images_scale": "2.0",
                    "image_export_mode": "embedded",
                    "to_formats": ["md", "json"] if is_excel else ["md"],
                }
                
                # 使用较短的超时，只是提交任务
                timeout_config = httpx.Timeout(connect=10.0, read=30.0, write=60.0, pool=10.0)
                with httpx.Client(timeout=timeout_config) as client:
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
                        return {"success": True, "task_id": task_id, "status": task_status}
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"提交异步任务失败: {error_msg}")
                        return {"success": False, "error": error_msg}
                        
        except Exception as e:
            logger.error(f"提交异步任务异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def submit_async_convert_async(self, file_path: str) -> Dict[str, Any]:
        """
        异步提交转换任务（推荐使用）
        
        使用异步 HTTP 客户端，不阻塞事件循环。
        
        Args:
            file_path: 文件路径
        
        Returns:
            Dict: {
                "success": bool,
                "task_id": str,
                "status": str,
                "error": str
            }
        """
        import aiofiles
        
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": f"文件不存在: {file_path}"}
        
        file_format = path.suffix.lstrip('.').lower()
        if file_format not in self.SUPPORTED_FORMATS:
            return {"success": False, "error": f"不支持的文件格式: {path.suffix}"}
        
        try:
            is_excel = file_format in ('xlsx', 'xls')
            
            # 异步读取文件
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            
            # 构建 multipart 数据
            files = {"files": (path.name, file_content, self._get_mime_type(file_format))}
            data = {
                "do_ocr": "true",
                "force_ocr": "true",  # 强制 OCR，确保扫描件/图片PDF被正确识别
                "ocr_engine": "rapidocr",
                "ocr_lang": "ch_sim,en",
                "table_mode": "accurate",
                "include_images": "true",
                "images_scale": "2.0",
                "image_export_mode": "embedded",
                "to_formats": ["md", "json"] if is_excel else ["md"],
            }
            
            # 使用异步 HTTP 客户端
            timeout_config = httpx.Timeout(connect=10.0, read=30.0, write=60.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{self.base_url}/v1/convert/file/async",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                
                if response.status_code in (200, 202):
                    result = response.json()
                    task_id = result.get("task_id") or result.get("id")
                    task_status = result.get("task_status") or result.get("status", "pending")
                    logger.info(f"[Async] 异步任务已提交: task_id={task_id}, status={task_status}")
                    return {"success": True, "task_id": task_id, "status": task_status}
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"[Async] 提交异步任务失败: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
        except Exception as e:
            logger.error(f"[Async] 提交异步任务异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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
            timeout_config = httpx.Timeout(
                connect=5.0,
                read=min(30.0, float(self.timeout)),
                write=min(30.0, float(self.timeout)),
                pool=min(30.0, float(self.timeout))
            )
            with httpx.Client(timeout=timeout_config) as client:
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
                    
                    # 如果任务成功但没有进度信息，设为 100%
                    if normalized_status == "success" and progress == 0:
                        progress = 100
                    # 注意：不再硬编码 started 状态为 50%
                    # 进度值由后端 loading_service 根据轮询次数逐步计算
                    
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
    
    def get_task_result(
        self,
        task_id: str,
        filename: Optional[str] = None,
        file_format: Optional[str] = None,
        figures_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        获取异步任务结果
        
        任务完成后调用此方法获取解析结果。
        
        Args:
            task_id: Docling Serve 返回的任务 ID
            filename: 原始文件名（用于元数据）
            file_format: 文件格式（如 xlsx、pdf 等，用于格式特定的元数据提取）
            figures_dir: 图片保存目录（可选，用于大图存储）
        
        Returns:
            Dict: 符合项目规范的解析结果（与 extract_text 返回格式一致）
        """
        try:
            timeout_config = httpx.Timeout(
                connect=10.0,
                read=self.timeout,
                write=self.timeout,
                pool=self.timeout
            )
            with httpx.Client(timeout=timeout_config) as client:
                response = client.get(
                    f"{self.base_url}/v1/result/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 复用现有的响应解析逻辑
                    actual_filename = filename or f"task_{task_id}"
                    actual_format = file_format or "unknown"
                    return self._parse_response(result, actual_filename, actual_format, figures_dir)
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
