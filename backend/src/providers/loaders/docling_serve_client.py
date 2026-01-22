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
        # 对 Excel 文件额外请求 JSON 格式以获取 Sheet 名称等元数据
        to_formats = ["md", "json"] if file_format in ('xlsx', 'xls') else ["md"]
        
        request_body = {
            "options": {
                "to_formats": to_formats,
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
            # 调试日志：打印响应结构的顶层 keys（仅对 Excel 文件）
            if file_format in ('xlsx', 'xls'):
                logger.info(f"[Excel Debug] Response top-level keys: {list(response.keys())}")
            
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
            
            # 从 Markdown 中提取图片信息（如果 Docling API 没有返回 figures）
            if not all_images:
                all_images = self._extract_images_from_markdown(full_text)
                if all_images:
                    logger.info(f"从 Markdown 中提取到 {len(all_images)} 张图片")
            
            # 关键：将内联 base64 图片转换为占位符格式
            # 目的：避免超长 base64 字符串干扰语义分块和消耗 token
            if all_images:
                original_len = len(full_text)
                full_text = self._convert_inline_images_to_placeholders(full_text, all_images)
                reduced_chars = original_len - len(full_text)
                if reduced_chars > 0:
                    logger.info(f"[图片占位符转换] 减少 {reduced_chars} 字符 ({reduced_chars / original_len * 100:.1f}%)")
            
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
            
            return result
            
        except Exception as e:
            logger.error(f"解析响应失败: {e}", exc_info=True)
            return {
                "success": False,
                "loader": self.name,
                "error": f"解析响应失败: {e}"
            }
    
    def _extract_images_from_markdown(self, md_content: str) -> List[Dict[str, Any]]:
        """
        从 Markdown 内容中提取图片信息
        
        Docling 生成的 Markdown 中图片格式为: ![alt](src)
        对于无法获取的图片，Docling 会生成: <!-- 🖼️❌ Image not available ... -->
        
        Args:
            md_content: Markdown 文本内容
        
        Returns:
            List[Dict]: 图片信息列表
        """
        import re
        images = []
        
        # 匹配 Markdown 图片语法: ![alt](src) 或 ![alt](src "title")
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')
        
        for idx, match in enumerate(img_pattern.finditer(md_content)):
            alt_text = match.group(1) or f'图片{idx + 1}'
            src = match.group(2)
            title = match.group(3)
            
            # 获取图片上下文（前后各100字符）
            start_pos = match.start()
            end_pos = match.end()
            
            context_before = md_content[max(0, start_pos - 100):start_pos].strip()
            context_after = md_content[end_pos:min(len(md_content), end_pos + 100)].strip()
            
            # 清理上下文中的换行
            context_before = ' '.join(context_before.split())
            context_after = ' '.join(context_after.split())
            
            # 检测图片类型
            image_type = self._detect_image_mime_type(src)
            
            # 检查是否为 base64
            is_base64 = src.startswith('data:') if src else False
            
            image_info = {
                "page_number": 1,
                "image_index": len(images),
                "src": src,
                "alt_text": alt_text,
                "title": title,
                "caption": title or alt_text,
                "mime_type": image_type,
                "is_base64": is_base64,
                "context_before": context_before if context_before else None,
                "context_after": context_after if context_after else None
            }
            
            # 如果是 base64，提取纯数据部分（去掉 data:image/xxx;base64, 前缀）
            if is_base64:
                # 分离 data URL 的 header 和数据部分
                if ',' in src:
                    image_info["base64_data"] = src.split(',', 1)[1]
                else:
                    image_info["base64_data"] = src
            
            images.append(image_info)
        
        # 同时匹配 Docling 的图片占位符注释: <!-- 🖼️❌ Image not available ... -->
        # 这表示 Docling 检测到了图片但无法提取
        placeholder_pattern = re.compile(
            r'([^\n]*)\n*<!-- 🖼️❌ Image not available[^>]*-->',
            re.MULTILINE
        )
        
        for match in placeholder_pattern.finditer(md_content):
            # 获取占位符前面的文本作为 alt_text
            preceding_text = match.group(1).strip()
            
            # 获取上下文
            start_pos = match.start()
            end_pos = match.end()
            
            context_before = md_content[max(0, start_pos - 150):start_pos].strip()
            context_after = md_content[end_pos:min(len(md_content), end_pos + 150)].strip()
            
            # 清理上下文
            context_before = ' '.join(context_before.split())
            context_after = ' '.join(context_after.split())
            
            # 从上下文中提取更多信息
            image_info = {
                "page_number": 1,
                "image_index": len(images),
                "src": None,  # Docling 无法获取图片URL
                "alt_text": preceding_text if preceding_text else f'图片{len(images) + 1}',
                "title": None,
                "caption": preceding_text,
                "mime_type": None,
                "is_base64": False,
                "extracted_from": "docling_placeholder",
                "context_before": context_before if context_before else None,
                "context_after": context_after if context_after else None
            }
            
            images.append(image_info)
        
        return images
    
    def _convert_inline_images_to_placeholders(
        self,
        md_content: str,
        images: List[Dict[str, Any]]
    ) -> str:
        """
        将 Markdown 中的内联 base64 图片转换为占位符格式
        
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
        import re
        
        if not images:
            return md_content
        
        result = md_content
        
        # 匹配所有 Markdown 图片（包括 base64 和普通 URL）
        # 使用非贪婪匹配来处理超长的 base64 字符串
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        
        # 找出所有匹配项并从后往前替换（避免位置偏移）
        matches = list(img_pattern.finditer(md_content))
        
        for idx, match in enumerate(reversed(matches)):
            img_idx = len(matches) - 1 - idx
            alt_text = match.group(1) or f'图片{img_idx + 1}'
            
            # 构建占位符: [IMAGE_N: 描述]
            placeholder = f"[IMAGE_{img_idx + 1}: {alt_text}]"
            
            # 替换原始图片标签
            result = result[:match.start()] + placeholder + result[match.end():]
        
        # 同时处理 Docling 的无效图片占位符: <!-- 🖼️❌ Image not available ... -->
        placeholder_pattern = re.compile(
            r'([^\n]*)\n*<!-- 🖼️❌ Image not available[^>]*-->',
            re.MULTILINE
        )
        placeholder_matches = list(placeholder_pattern.finditer(result))
        
        # 占位符图片的索引从 Markdown 图片之后开始
        start_idx = len(matches)
        
        for idx, match in enumerate(reversed(placeholder_matches)):
            img_idx = start_idx + len(placeholder_matches) - 1 - idx
            alt_text = match.group(1).strip() or f'图片{img_idx + 1}'
            
            placeholder = f"[IMAGE_{img_idx + 1}: {alt_text}]"
            result = result[:match.start()] + placeholder + result[match.end():]
        
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
        
        if detail_parts:
            return f"\n[IMAGE_{idx}] ({' '.join(detail_parts)})\n"
        else:
            return f"\n[IMAGE_{idx}]\n"
    
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
            # 对 Excel 文件额外请求 JSON 格式以获取 Sheet 名称等元数据
            is_excel = file_format in ('xlsx', 'xls')
            
            with open(file_path, 'rb') as f:
                files = {"files": (path.name, f, self._get_mime_type(file_format))}
                
                # 构建 data 字典
                # 对于需要传递多个值的字段（如 to_formats），使用列表
                data = {
                    "do_ocr": "true",
                    "force_ocr": "true",
                    "ocr_engine": "rapidocr",
                    "ocr_lang": "ch_sim,en",
                    "table_mode": "accurate",
                    "include_images": "true",
                    "images_scale": "2.0",
                    "image_export_mode": "embedded",
                    "to_formats": ["md", "json"] if is_excel else ["md"],
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
    
    def get_task_result(
        self,
        task_id: str,
        filename: Optional[str] = None,
        file_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取异步任务结果
        
        任务完成后调用此方法获取解析结果。
        
        Args:
            task_id: Docling Serve 返回的任务 ID
            filename: 原始文件名（用于元数据）
            file_format: 文件格式（如 xlsx、pdf 等，用于格式特定的元数据提取）
        
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
                    actual_filename = filename or f"task_{task_id}"
                    actual_format = file_format or "unknown"
                    return self._parse_response(result, actual_filename, actual_format)
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
