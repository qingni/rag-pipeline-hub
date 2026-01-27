"""Multimodal chunker for handling tables, images, and code blocks."""
import re
import uuid
import base64
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .base_chunker import BaseChunker
from ...models.chunk_metadata import (
    ChunkTypeEnum,
    create_chunk_metadata
)


class MultimodalChunker(BaseChunker):
    """
    Chunker that extracts and processes multimodal content (tables, images, code blocks)
    from documents, generating separate chunks for each content type.
    
    This chunker:
    1. Extracts tables (Markdown format) as independent chunks
    2. Extracts images (with base64 or path) as independent chunks  
    3. Extracts code blocks as independent chunks
    4. Chunks remaining text using a configurable text strategy
    """
    
    # Regex patterns for content extraction
    # Fixed: last row may not end with \n, so use \n? at the end
    TABLE_PATTERN = re.compile(
        r'(\|[^\n]+\|(?:\n\|[-:| ]+\|)?(?:\n\|[^\n]+\|)*)',
        re.MULTILINE
    )
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\n([\s\S]*?)```',
        re.MULTILINE
    )
    
    IMAGE_PATTERN = re.compile(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        re.MULTILINE
    )
    
    # HTML image pattern
    HTML_IMAGE_PATTERN = re.compile(
        r'<img[^>]+src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*/?>',
        re.IGNORECASE
    )
    
    # 占位符格式匹配（匹配 [IMAGE_N: 描述] 格式）
    # 用于识别文档加载阶段生成的图片占位符
    PLACEHOLDER_IMAGE_PATTERN = re.compile(
        r'\[IMAGE_(\d+):\s*([^\]]*)\]',
        re.MULTILINE
    )
    
    def __init__(self, **params):
        """
        Initialize multimodal chunker.
        
        Args:
            include_tables: Whether to extract tables (default: True)
            include_images: Whether to extract images (default: True)
            include_code: Whether to extract code blocks (default: True)
            text_strategy: Strategy for text chunks ('character', 'paragraph') (default: 'character')
            text_chunk_size: Size for text chunks (default: 500)
            text_overlap: Overlap for text chunks (default: 50)
            min_table_rows: Minimum rows for table extraction (default: 2)
            min_code_lines: Minimum lines for code extraction (default: 3)
            extract_image_base64: Whether to convert images to base64 (default: False)
            image_base_path: Base path for resolving relative image paths
        """
        super().__init__(**params)
    
    def validate_params(self) -> None:
        """Validate chunking parameters."""
        # Boolean parameters
        self.include_tables = self.params.get('include_tables', True)
        self.include_images = self.params.get('include_images', True)
        self.include_code = self.params.get('include_code', True)
        
        # Text chunking parameters
        self.text_strategy = self.params.get('text_strategy', 'character')
        if self.text_strategy not in ('character', 'paragraph', 'none'):
            raise ValueError(f"Invalid text_strategy: {self.text_strategy}")
        
        self.text_chunk_size = self.params.get('text_chunk_size', 500)
        if not 100 <= self.text_chunk_size <= 5000:
            raise ValueError("text_chunk_size must be between 100 and 5000")
        
        self.text_overlap = self.params.get('text_overlap', 50)
        if self.text_overlap >= self.text_chunk_size:
            raise ValueError("text_overlap must be less than text_chunk_size")
        
        # Extraction thresholds
        self.min_table_rows = self.params.get('min_table_rows', 2)
        self.min_code_lines = self.params.get('min_code_lines', 3)
        
        # Image processing
        self.extract_image_base64 = self.params.get('extract_image_base64', False)
        self.image_base_path = self.params.get('image_base_path', None)
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text with multimodal content extraction.
        
        For Excel files with page metadata, each sheet is processed independently
        to ensure proper sheet_name association.
        
        Args:
            text: Input text with potential tables, images, and code
            metadata: Optional metadata about the source document
                     Expected format: {"pages": [{"page_number": 1, "sheet_name": "xxx", "text": "...", ...}], ...}
        
        Returns:
            List of chunks with appropriate types (text, table, image, code)
        """
        metadata = metadata or {}
        pages = metadata.get("pages", [])
        
        # Check if we have page-level data with sheet_name (Excel files)
        # If so, process each page independently to preserve sheet boundaries
        has_sheet_pages = pages and any(p.get("sheet_name") for p in pages)
        
        if has_sheet_pages:
            return self._chunk_by_pages(pages, metadata)
        else:
            return self._chunk_full_text(text, metadata)
    
    def _chunk_by_pages(
        self, 
        pages: List[Dict[str, Any]], 
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk document by pages, treating each page/sheet as an independent unit.
        This ensures Excel sheet boundaries are preserved.
        
        Args:
            pages: List of page data with text, sheet_name, etc.
            metadata: Document metadata
            
        Returns:
            List of chunks with proper sheet_name in metadata
        """
        all_chunks = []
        global_offset = 0
        
        for page in pages:
            page_text = page.get("text", "")
            sheet_name = page.get("sheet_name")
            page_number = page.get("page_number")
            
            if not page_text.strip():
                global_offset += len(page_text) + 2  # +2 for separator
                continue
            
            # Create page-specific metadata
            page_metadata = {
                **metadata,
                "current_sheet_name": sheet_name,
                "current_page_number": page_number
            }
            
            # Check if the content is a TSV table (openpyxl format)
            # TSV tables have tab-separated values
            is_tsv_table = self._is_tsv_table(page_text)
            
            if is_tsv_table and self.include_tables:
                # Treat entire page as a single table chunk
                chunk = self._create_tsv_table_chunk(
                    page_text, 
                    global_offset, 
                    sheet_name, 
                    page_number,
                    len(all_chunks)
                )
                all_chunks.append(chunk)
            else:
                # Process page with standard multimodal extraction
                page_chunks = self._chunk_single_page(
                    page_text, 
                    global_offset, 
                    sheet_name,
                    page_number,
                    page_metadata
                )
                all_chunks.extend(page_chunks)
            
            global_offset += len(page_text) + 2  # +2 for "\n\n" separator
        
        # Reassign global chunk indices
        for idx, chunk in enumerate(all_chunks):
            chunk['metadata']['chunk_index'] = idx
        
        return all_chunks
    
    def _is_tsv_table(self, text: str) -> bool:
        """
        Check if text is a TSV (Tab-Separated Values) table.
        TSV tables from openpyxl have tab-separated columns.
        """
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check if most lines have tabs (indicating TSV format)
        tab_lines = sum(1 for line in lines if '\t' in line)
        return tab_lines >= len(lines) * 0.5  # At least 50% lines have tabs
    
    def _create_tsv_table_chunk(
        self, 
        text: str, 
        offset: int, 
        sheet_name: Optional[str],
        page_number: Optional[int],
        chunk_index: int
    ) -> Dict[str, Any]:
        """Create a table chunk from TSV formatted text."""
        lines = text.strip().split('\n')
        
        # Skip "Sheet: xxx" header line if present
        data_lines = []
        for line in lines:
            if line.startswith("Sheet:"):
                continue
            data_lines.append(line)
        
        # Count rows and columns
        row_count = len(data_lines)
        col_count = max(len(line.split('\t')) for line in data_lines) if data_lines else 0
        
        # Extract headers (first data row with tabs)
        headers = []
        for line in data_lines:
            if '\t' in line:
                headers = [h.strip() for h in line.split('\t')]
                break
        
        table_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.TABLE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=text,
            start_position=offset,
            end_position=offset + len(text),
            table_markdown=text,
            row_count=row_count,
            column_count=col_count,
            headers=headers,
            has_header=True,
            sheet_name=sheet_name
        )
        
        # Add page_number to metadata
        if page_number is not None:
            table_metadata['page_number'] = page_number
        
        return {
            'content': text,
            'chunk_type': ChunkTypeEnum.TABLE.value,
            'parent_id': None,
            'metadata': table_metadata
        }
    
    def _chunk_single_page(
        self, 
        text: str, 
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Chunk a single page with multimodal content extraction.
        All chunks from this page will inherit the sheet_name.
        """
        chunks = []
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract Markdown tables
        if self.include_tables:
            table_chunks, table_regions = self._extract_tables_from_page(
                text, global_offset, sheet_name, page_number, metadata
            )
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks  
        if self.include_code:
            code_chunks, code_regions = self._extract_code_from_page(
                text, global_offset, sheet_name, page_number, metadata
            )
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract images
        if self.include_images:
            image_chunks, image_regions = self._extract_images_from_page(
                text, global_offset, sheet_name, page_number, metadata
            )
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract remaining text
        if self.text_strategy != 'none':
            text_chunks = self._extract_text_from_page(
                text, global_offset, extracted_regions, sheet_name, page_number, metadata
            )
            chunks.extend(text_chunks)
        
        return chunks
    
    def _extract_tables_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract Markdown tables from a single page."""
        chunks = []
        regions = []
        
        for match in self.TABLE_PATTERN.finditer(text):
            table_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            rows = [r.strip() for r in table_text.split('\n') if r.strip()]
            if len(rows) < self.min_table_rows:
                continue
            
            # Parse headers
            headers = self._parse_table_headers(rows[0]) if rows else []
            
            # Check for separator row
            has_separator = len(rows) > 1 and re.match(r'^\|[-:| ]+\|$', rows[1])
            data_row_count = len(rows) - (2 if has_separator else 1)
            
            table_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TABLE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=table_text,
                start_position=global_offset + start_pos,
                end_position=global_offset + end_pos,
                table_markdown=table_text,
                row_count=data_row_count,
                column_count=len(headers),
                headers=headers,
                has_header=True,
                sheet_name=sheet_name
            )
            
            if page_number is not None:
                table_metadata['page_number'] = page_number
            
            chunks.append({
                'content': table_text,
                'chunk_type': ChunkTypeEnum.TABLE.value,
                'parent_id': None,
                'metadata': table_metadata
            })
            
            regions.append((start_pos, end_pos, 'table'))
        
        return chunks, regions
    
    def _extract_code_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract code blocks from a single page."""
        chunks = []
        regions = []
        
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            lines = code_content.split('\n')
            if len(lines) < self.min_code_lines:
                continue
            
            # Detect function/class names
            function_name = None
            class_name = None
            
            func_match = re.search(r'def\s+(\w+)\s*\(', code_content)
            if func_match:
                function_name = func_match.group(1)
            
            class_match = re.search(r'class\s+(\w+)[\s:(]', code_content)
            if class_match:
                class_name = class_match.group(1)
            
            code_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.CODE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=code_content,
                start_position=global_offset + start_pos,
                end_position=global_offset + end_pos,
                language=language,
                start_line=1,
                end_line=len(lines),
                function_name=function_name,
                class_name=class_name,
                is_complete_block=True
            )
            
            if sheet_name:
                code_metadata['sheet_name'] = sheet_name
            if page_number is not None:
                code_metadata['page_number'] = page_number
            
            chunks.append({
                'content': code_content,
                'chunk_type': ChunkTypeEnum.CODE.value,
                'parent_id': None,
                'metadata': code_metadata
            })
            
            regions.append((start_pos, end_pos, 'code'))
        
        return chunks, regions
    
    def _extract_images_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """
        Extract images from a single page.
        
        支持三种图片格式的识别：
        1. 占位符格式 [IMAGE_N: 描述] - 文档加载阶段生成，关联 images 数组数据
        2. Markdown 格式 ![alt](path)
        3. HTML 格式 <img src="..." />
        
        占位符+结构化元数据方案：
        - 占位符格式优先匹配，从 metadata.images 获取完整图片数据
        - 图片数据包含 file_path（用于展示）和 base64_data（用于多模态嵌入）
        """
        chunks = []
        regions = []
        
        # 获取预加载的图片数据（来自文档加载阶段）
        images_data = metadata.get("images", [])
        
        # 方式1：匹配占位符格式并关联图片数据 [IMAGE_N: 描述]
        for match in self.PLACEHOLDER_IMAGE_PATTERN.finditer(text):
            image_index = int(match.group(1))
            placeholder_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # 查找对应的图片数据
            image_info = self._find_image_by_index(images_data, image_index, page_number)
            
            if image_info:
                # 从加载结果创建图片块（包含完整数据）
                image_chunk = self._create_image_chunk_from_data(
                    image_info=image_info,
                    placeholder_text=placeholder_text,
                    start_pos=global_offset + start_pos,
                    end_pos=global_offset + end_pos,
                    chunk_index=len(chunks),
                    sheet_name=sheet_name,
                    page_number=page_number
                )
                if image_chunk:
                    chunks.append(image_chunk)
                    regions.append((start_pos, end_pos, 'image'))
            else:
                # 没有找到对应图片数据，创建基本图片块
                image_chunk = self._create_placeholder_image_chunk(
                    placeholder_text=placeholder_text,
                    image_index=image_index,
                    start_pos=global_offset + start_pos,
                    end_pos=global_offset + end_pos,
                    chunk_index=len(chunks),
                    sheet_name=sheet_name,
                    page_number=page_number
                )
                if image_chunk:
                    chunks.append(image_chunk)
                    regions.append((start_pos, end_pos, 'image'))
        
        # 方式2：匹配 Markdown 图片格式 ![alt](path)
        for match in self.IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            # 跳过已被占位符匹配的区域
            if any(r[0] <= start_pos < r[1] for r in regions):
                continue
                
            alt_text = match.group(1)
            image_path = match.group(2)
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk_with_sheet(
                image_path=image_path,
                alt_text=alt_text,
                start_pos=global_offset + start_pos,
                end_pos=global_offset + end_pos,
                chunk_index=len(chunks),
                sheet_name=sheet_name,
                page_number=page_number,
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        # 方式3：匹配 HTML 图片格式 <img src="..." />
        for match in self.HTML_IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            # 跳过已匹配的区域
            if any(r[0] <= start_pos < r[1] for r in regions):
                continue
            
            image_path = match.group(1)
            alt_text = match.group(2) if match.lastindex >= 2 else ''
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk_with_sheet(
                image_path=image_path,
                alt_text=alt_text or '',
                start_pos=global_offset + start_pos,
                end_pos=global_offset + end_pos,
                chunk_index=len(chunks),
                sheet_name=sheet_name,
                page_number=page_number,
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        return chunks, regions
    
    def _find_image_by_index(
        self, 
        images_data: List[Dict[str, Any]], 
        image_index: int, 
        page_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据图片索引查找图片数据。
        
        Args:
            images_data: 图片数组（来自文档加载结果）
            image_index: 图片索引（占位符中的数字）
            page_number: 页码（可选，用于精确匹配）
            
        Returns:
            匹配的图片数据，或 None
        """
        for img in images_data:
            if img.get("image_index") == image_index:
                # 如果指定了页码，验证页码匹配
                if page_number is not None:
                    img_page = img.get("page_number")
                    if img_page is not None and img_page != page_number:
                        continue
                return img
        return None
    
    def _create_image_chunk_from_data(
        self,
        image_info: Dict[str, Any],
        placeholder_text: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Dict[str, Any]:
        """
        从加载阶段的图片数据创建图片块。
        
        这是占位符+结构化元数据方案的核心方法：
        - 图片块的 content 使用可读的描述文本
        - metadata 包含完整的图片数据（file_path 用于展示，base64_data 用于嵌入）
        
        业内最佳实践：按需加载
        - 如果 base64_data 已存在，直接使用
        - 如果只有 file_path，在需要时才加载（嵌入阶段）
        - 优先使用缩略图用于预览
        
        Args:
            image_info: 图片数据（来自加载结果的 images 数组）
            placeholder_text: 占位符中的描述文本
            start_pos: 在文档中的起始位置
            end_pos: 在文档中的结束位置
            chunk_index: 块索引
            sheet_name: 工作表名称
            page_number: 页码
            
        Returns:
            图片块字典
        """
        # 确定图片描述（优先使用 alt_text，其次 caption，最后用 placeholder_text）
        alt_text = image_info.get("alt_text") or image_info.get("caption") or placeholder_text
        content = f"[Image: {alt_text}]" if alt_text else "[Image]"
        
        # 提取图片属性
        file_path = image_info.get("file_path")
        base64_data = image_info.get("base64_data")
        thumbnail_base64 = image_info.get("thumbnail_base64")
        mime_type = image_info.get("mime_type")
        width = image_info.get("width")
        height = image_info.get("height")
        original_size = image_info.get("original_size")
        context_before = image_info.get("context_before")
        context_after = image_info.get("context_after")
        
        # 按需加载：如果没有 base64_data 但有 file_path，从文件加载
        # 这里仅在需要时加载，避免内存占用过大
        image_base64_for_embedding = base64_data
        if not image_base64_for_embedding and file_path:
            try:
                with open(file_path, 'rb') as f:
                    image_base64_for_embedding = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"按需加载图片失败 {file_path}: {e}")
        
        # 从文件路径推断格式
        img_format = None
        if mime_type:
            img_format = mime_type.split('/')[-1] if '/' in mime_type else mime_type
        elif file_path:
            img_format = Path(file_path).suffix.lstrip('.').lower()
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            # 核心图片数据（支持多模态处理）
            image_path=file_path,           # 用于前端展示
            image_base64=image_base64_for_embedding,  # 用于多模态嵌入
            thumbnail_base64=thumbnail_base64,  # 用于快速预览
            alt_text=alt_text,
            caption=image_info.get("caption"),
            width=width,
            height=height,
            original_size=original_size,
            format=img_format,
            mime_type=mime_type,
            # 图片上下文（提升检索相关性）
            context_before=context_before,
            context_after=context_after,
            # 原始图片索引
            image_index=image_info.get("image_index")
        )
        
        # 添加工作表和页码信息
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _create_placeholder_image_chunk(
        self,
        placeholder_text: str,
        image_index: int,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Dict[str, Any]:
        """
        创建基于占位符的图片块（没有找到对应图片数据时使用）。
        """
        content = f"[Image: {placeholder_text}]" if placeholder_text else "[Image]"
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            alt_text=placeholder_text,
            image_index=image_index
        )
        
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _create_image_chunk_with_sheet(
        self,
        image_path: str,
        alt_text: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create an image chunk with sheet_name support."""
        image_base64 = None
        width = None
        height = None
        img_format = None
        
        if self.extract_image_base64:
            base64_data, w, h, fmt = self._load_image_as_base64(image_path)
            if base64_data:
                image_base64 = base64_data
                width = w
                height = h
                img_format = fmt
        
        if not img_format and image_path:
            img_format = Path(image_path).suffix.lstrip('.').lower()
        
        content = f"[Image: {alt_text}]" if alt_text else f"[Image: {image_path}]"
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            image_path=image_path,
            alt_text=alt_text,
            format=img_format,
            width=width,
            height=height,
            image_base64=image_base64
        )
        
        if sheet_name:
            image_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            image_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _extract_text_from_page(
        self,
        text: str,
        global_offset: int,
        extracted_regions: List[Tuple[int, int, str]],
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract text chunks from a single page, excluding already extracted regions."""
        chunks = []
        
        # Sort regions by start position
        sorted_regions = sorted(extracted_regions, key=lambda r: r[0])
        
        # Find text segments
        text_segments = []
        current_pos = 0
        
        for start, end, _ in sorted_regions:
            if current_pos < start:
                text_segments.append((current_pos, start))
            current_pos = max(current_pos, end)
        
        if current_pos < len(text):
            text_segments.append((current_pos, len(text)))
        
        # Chunk each text segment
        for seg_start, seg_end in text_segments:
            segment_text = text[seg_start:seg_end].strip()
            if not segment_text:
                continue
            
            if self.text_strategy == 'character':
                segment_chunks = self._chunk_text_by_character_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number, metadata
                )
            else:  # paragraph
                segment_chunks = self._chunk_text_by_paragraph_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number, metadata
                )
            
            chunks.extend(segment_chunks)
        
        return chunks
    
    def _chunk_text_by_character_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by character with sheet_name support."""
        chunks = []
        step = self.text_chunk_size - self.text_overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.text_chunk_size]
            if not chunk_text.strip():
                continue
            
            chunk = self._create_chunk_with_sheet(
                content=chunk_text,
                index=len(chunks),
                start_pos=offset + i,
                end_pos=offset + i + len(chunk_text),
                chunk_type=ChunkTypeEnum.TEXT.value,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_text_by_paragraph_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by paragraph with sheet_name support."""
        chunks = []
        
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_pos = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                current_pos += 2
                continue
            
            para_start = text.find(para, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(para)
            
            chunk = self._create_chunk_with_sheet(
                content=para,
                index=len(chunks),
                start_pos=offset + para_start,
                end_pos=offset + para_end,
                chunk_type=ChunkTypeEnum.TEXT.value,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.append(chunk)
            
            current_pos = para_end
        
        return chunks
    
    def _create_chunk_with_sheet(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        chunk_type: str,
        sheet_name: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a chunk with sheet_name in metadata."""
        chunk_metadata = create_chunk_metadata(
            chunk_type=chunk_type,
            chunk_id=str(uuid.uuid4()),
            chunk_index=index,
            content=content,
            start_position=start_pos,
            end_position=end_pos
        )
        
        if sheet_name:
            chunk_metadata['sheet_name'] = sheet_name
        if page_number is not None:
            chunk_metadata['page_number'] = page_number
        
        return {
            'content': content,
            'chunk_type': chunk_type,
            'parent_id': None,
            'metadata': chunk_metadata
        }
    
    def _chunk_full_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Original chunking logic for documents without page/sheet structure.
        """
        chunks = []
        
        # Build position-to-sheet mapping for Excel files (legacy support)
        sheet_position_map = self._build_position_to_sheet_map(text, metadata.get("pages", []))
        
        # Track extracted regions to avoid double-processing
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract tables (with sheet_name support)
        if self.include_tables:
            table_chunks, table_regions = self._extract_tables(text, metadata, sheet_position_map)
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks
        if self.include_code:
            code_chunks, code_regions = self._extract_code_blocks(text, metadata)
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract images
        if self.include_images:
            image_chunks, image_regions = self._extract_images(text, metadata)
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract remaining text
        if self.text_strategy != 'none':
            text_chunks = self._extract_text(text, extracted_regions, metadata)
            chunks.extend(text_chunks)
        
        # Sort all chunks by position
        chunks.sort(key=lambda c: c['metadata'].get('start_position', 0))
        
        # Reassign sequence numbers
        for idx, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = idx
        
        return chunks
    
    def _build_position_to_sheet_map(
        self, 
        text: str, 
        pages: List[Dict[str, Any]]
    ) -> List[Tuple[int, int, Optional[str]]]:
        """
        Build a map of text position ranges to sheet names.
        
        Args:
            text: Full document text
            pages: List of page metadata with sheet_name info
        
        Returns:
            List of (start_pos, end_pos, sheet_name) tuples
        """
        if not pages:
            return []
        
        position_map = []
        current_pos = 0
        
        for page in pages:
            sheet_name = page.get("sheet_name")
            char_count = page.get("char_count", 0)
            
            if not sheet_name:
                # Skip pages without sheet_name, but update position
                current_pos += char_count + 2  # +2 for "\n\n" separator
                continue
            
            # Calculate page boundaries based on char_count
            page_start = current_pos
            page_end = current_pos + char_count
            
            position_map.append((page_start, page_end, sheet_name))
            current_pos = page_end + 2  # +2 for "\n\n" separator
        
        return position_map
    
    def _get_sheet_name_for_position(
        self, 
        position: int, 
        sheet_map: List[Tuple[int, int, Optional[str]]]
    ) -> Optional[str]:
        """Get sheet name for a given position in text."""
        for start, end, sheet_name in sheet_map:
            if start <= position < end:
                return sheet_name
        return None
    
    def _extract_tables(
        self, 
        text: str, 
        metadata: Dict[str, Any],
        sheet_position_map: List[Tuple[int, int, Optional[str]]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """
        Extract table chunks from text.
        
        Args:
            text: Input text
            metadata: Document metadata
            sheet_position_map: Mapping of positions to sheet names for Excel files
        """
        chunks = []
        regions = []
        sheet_position_map = sheet_position_map or []
        
        for match in self.TABLE_PATTERN.finditer(text):
            table_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Parse table structure
            rows = [r.strip() for r in table_text.split('\n') if r.strip()]
            
            # Skip separator rows for counting
            data_rows = [r for r in rows if not re.match(r'^\|[-:| ]+\|$', r)]
            
            if len(data_rows) < self.min_table_rows:
                continue
            
            # Count columns
            first_row = data_rows[0] if data_rows else ""
            column_count = first_row.count('|') - 1 if first_row else 0
            
            # Check for header (presence of separator row)
            has_header = any(re.match(r'^\|[-:| ]+\|$', r) for r in rows)
            
            # Determine sheet_name based on position
            sheet_name = self._get_sheet_name_for_position(start_pos, sheet_position_map)
            
            # Create table chunk
            table_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TABLE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=table_text,
                start_position=start_pos,
                end_position=end_pos,
                table_index=len([c for c in chunks if c.get('chunk_type') == 'table']),
                row_count=len(data_rows),
                column_count=column_count,
                has_header=has_header,
                table_markdown=table_text,
                page_number=metadata.get('page_number'),
                sheet_name=sheet_name  # Include sheet_name for Excel files
            )
            
            chunks.append({
                'content': table_text,
                'chunk_type': ChunkTypeEnum.TABLE.value,
                'parent_id': None,
                'metadata': table_metadata
            })
            
            regions.append((start_pos, end_pos, 'table'))
        
        return chunks, regions
    
    def _extract_code_blocks(
        self, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """Extract code block chunks from text."""
        chunks = []
        regions = []
        
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Check minimum lines
            lines = code_content.split('\n')
            if len(lines) < self.min_code_lines:
                continue
            
            # Detect function/class names (basic detection)
            function_name = None
            class_name = None
            
            # Python detection
            func_match = re.search(r'def\s+(\w+)\s*\(', code_content)
            if func_match:
                function_name = func_match.group(1)
            
            class_match = re.search(r'class\s+(\w+)[\s:(]', code_content)
            if class_match:
                class_name = class_match.group(1)
            
            # Create code chunk
            code_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.CODE.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=code_content,
                start_position=start_pos,
                end_position=end_pos,
                language=language,
                start_line=1,
                end_line=len(lines),
                function_name=function_name,
                class_name=class_name,
                is_complete_block=True
            )
            
            chunks.append({
                'content': code_content,
                'chunk_type': ChunkTypeEnum.CODE.value,
                'parent_id': None,
                'metadata': code_metadata
            })
            
            regions.append((start_pos, end_pos, 'code'))
        
        return chunks, regions
    
    def _extract_images(
        self, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """
        Extract image chunks from text (full text mode).
        
        支持三种图片格式：
        1. 占位符格式 [IMAGE_N: 描述] - 关联 metadata.images 数据
        2. Markdown 格式 ![alt](path)
        3. HTML 格式 <img src="..." />
        """
        chunks = []
        regions = []
        
        # 获取预加载的图片数据
        images_data = metadata.get("images", [])
        
        # 方式1：匹配占位符格式 [IMAGE_N: 描述]
        for match in self.PLACEHOLDER_IMAGE_PATTERN.finditer(text):
            image_index = int(match.group(1))
            placeholder_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # 查找对应的图片数据
            image_info = self._find_image_by_index(images_data, image_index)
            
            if image_info:
                image_chunk = self._create_image_chunk_from_data(
                    image_info=image_info,
                    placeholder_text=placeholder_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    chunk_index=len(chunks),
                    sheet_name=None,
                    page_number=image_info.get("page_number")
                )
                if image_chunk:
                    chunks.append(image_chunk)
                    regions.append((start_pos, end_pos, 'image'))
            else:
                image_chunk = self._create_placeholder_image_chunk(
                    placeholder_text=placeholder_text,
                    image_index=image_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    chunk_index=len(chunks),
                    sheet_name=None,
                    page_number=None
                )
                if image_chunk:
                    chunks.append(image_chunk)
                    regions.append((start_pos, end_pos, 'image'))
        
        # 方式2：匹配 Markdown 图片格式
        for match in self.IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            if any(r[0] <= start_pos < r[1] for r in regions):
                continue
                
            alt_text = match.group(1)
            image_path = match.group(2)
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk(
                image_path=image_path,
                alt_text=alt_text,
                start_pos=start_pos,
                end_pos=end_pos,
                chunk_index=len(chunks),
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        # 方式3：匹配 HTML 图片格式
        for match in self.HTML_IMAGE_PATTERN.finditer(text):
            start_pos = match.start()
            if any(r[0] <= start_pos < r[1] for r in regions):
                continue
            
            image_path = match.group(1)
            alt_text = match.group(2) if match.lastindex >= 2 else ''
            end_pos = match.end()
            
            image_chunk = self._create_image_chunk(
                image_path=image_path,
                alt_text=alt_text or '',
                start_pos=start_pos,
                end_pos=end_pos,
                chunk_index=len(chunks),
                metadata=metadata
            )
            
            if image_chunk:
                chunks.append(image_chunk)
                regions.append((start_pos, end_pos, 'image'))
        
        return chunks, regions
    
    def _create_image_chunk(
        self,
        image_path: str,
        alt_text: str,
        start_pos: int,
        end_pos: int,
        chunk_index: int,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create an image chunk with optional base64 encoding."""
        image_base64 = None
        width = None
        height = None
        img_format = None
        
        # Try to get image info and base64
        if self.extract_image_base64:
            base64_data, w, h, fmt = self._load_image_as_base64(image_path)
            if base64_data:
                image_base64 = base64_data
                width = w
                height = h
                img_format = fmt
        
        # Determine format from path
        if not img_format and image_path:
            img_format = Path(image_path).suffix.lstrip('.').lower()
        
        # Content for image chunk (description or path)
        content = f"[Image: {alt_text}]" if alt_text else f"[Image: {image_path}]"
        
        image_metadata = create_chunk_metadata(
            chunk_type=ChunkTypeEnum.IMAGE.value,
            chunk_id=str(uuid.uuid4()),
            chunk_index=chunk_index,
            content=content,
            start_position=start_pos,
            end_position=end_pos,
            image_index=chunk_index,
            image_path=image_path,
            image_base64=image_base64,
            alt_text=alt_text,
            caption=alt_text,
            width=width,
            height=height,
            format=img_format,
            page_number=metadata.get('page_number')
        )
        
        return {
            'content': content,
            'chunk_type': ChunkTypeEnum.IMAGE.value,
            'parent_id': None,
            'metadata': image_metadata
        }
    
    def _load_image_as_base64(
        self, 
        image_path: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """
        Load image and convert to base64 for multimodal embedding support.
        
        Supports:
        - Local file paths (absolute and relative)
        - HTTP/HTTPS URLs (with fetch)
        - Data URLs (extract existing base64)
        
        Returns:
            Tuple of (base64_string, width, height, format) or (None, None, None, None)
        """
        try:
            # Handle data URLs
            if image_path.startswith('data:'):
                return self._extract_data_url_base64(image_path)
            
            # Handle HTTP/HTTPS URLs
            if image_path.startswith(('http://', 'https://')):
                return self._fetch_url_image_base64(image_path)
            
            # Handle local file paths
            return self._load_local_image_base64(image_path)
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to load image {image_path}: {e}")
            return None, None, None, None
    
    def _extract_data_url_base64(
        self, 
        data_url: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Extract base64 from data URL."""
        import re
        
        # Parse data URL: data:image/png;base64,xxxxx
        match = re.match(r'data:image/(\w+);base64,(.+)', data_url)
        if not match:
            return None, None, None, None
        
        img_format = match.group(1)
        base64_str = match.group(2)
        
        # Try to get dimensions
        width, height = self._get_base64_image_dimensions(base64_str)
        
        return base64_str, width, height, img_format
    
    def _fetch_url_image_base64(
        self, 
        url: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Fetch image from URL and convert to base64."""
        try:
            import requests
            from io import BytesIO
            
            # Fetch with timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            image_data = response.content
            base64_str = base64.b64encode(image_data).decode('utf-8')
            
            # Detect format from content-type or URL
            content_type = response.headers.get('content-type', '')
            if 'png' in content_type:
                img_format = 'png'
            elif 'gif' in content_type:
                img_format = 'gif'
            elif 'webp' in content_type:
                img_format = 'webp'
            else:
                img_format = 'jpeg'  # Default
            
            # Try to get dimensions
            width, height = None, None
            try:
                from PIL import Image
                img = Image.open(BytesIO(image_data))
                width, height = img.size
            except ImportError:
                pass
            
            return base64_str, width, height, img_format
            
        except Exception:
            return None, None, None, None
    
    def _load_local_image_base64(
        self, 
        image_path: str
    ) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
        """Load local image file and convert to base64."""
        # Resolve relative path
        if self.image_base_path and not Path(image_path).is_absolute():
            full_path = Path(self.image_base_path) / image_path
        else:
            full_path = Path(image_path)
        
        if not full_path.exists():
            return None, None, None, None
        
        # Read and encode image
        with open(full_path, 'rb') as f:
            image_data = f.read()
        
        base64_str = base64.b64encode(image_data).decode('utf-8')
        img_format = full_path.suffix.lstrip('.').lower()
        
        # Try to get dimensions
        width, height = None, None
        try:
            from PIL import Image
            img = Image.open(full_path)
            width, height = img.size
        except ImportError:
            pass
        
        return base64_str, width, height, img_format
    
    def _get_base64_image_dimensions(
        self, 
        base64_str: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """Get dimensions from base64 encoded image."""
        try:
            from PIL import Image
            from io import BytesIO
            
            image_data = base64.b64decode(base64_str)
            img = Image.open(BytesIO(image_data))
            return img.size
        except Exception:
            return None, None
    
    def _extract_text(
        self, 
        text: str, 
        extracted_regions: List[Tuple[int, int, str]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract text chunks from regions not covered by other content types."""
        chunks = []
        
        # Sort regions by start position
        sorted_regions = sorted(extracted_regions, key=lambda r: r[0])
        
        # Find text segments
        text_segments = []
        current_pos = 0
        
        for start, end, _ in sorted_regions:
            if current_pos < start:
                text_segments.append((current_pos, start))
            current_pos = max(current_pos, end)
        
        # Add final segment
        if current_pos < len(text):
            text_segments.append((current_pos, len(text)))
        
        # Chunk each text segment
        for seg_start, seg_end in text_segments:
            segment_text = text[seg_start:seg_end].strip()
            if not segment_text:
                continue
            
            if self.text_strategy == 'character':
                segment_chunks = self._chunk_text_by_character(
                    segment_text, seg_start, metadata
                )
            else:  # paragraph
                segment_chunks = self._chunk_text_by_paragraph(
                    segment_text, seg_start, metadata
                )
            
            chunks.extend(segment_chunks)
        
        return chunks
    
    def _chunk_text_by_character(
        self, 
        text: str, 
        offset: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text using character-based splitting."""
        chunks = []
        step = self.text_chunk_size - self.text_overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.text_chunk_size]
            if not chunk_text.strip():
                continue
            
            chunk = self._create_chunk(
                content=chunk_text,
                index=len(chunks),
                start_pos=offset + i,
                end_pos=offset + i + len(chunk_text),
                chunk_type=ChunkTypeEnum.TEXT.value
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_text_by_paragraph(
        self, 
        text: str, 
        offset: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunk text by paragraphs."""
        chunks = []
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', text)
        
        current_pos = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                current_pos += 2  # Skip empty paragraph
                continue
            
            # Find actual position in original text
            para_start = text.find(para, current_pos)
            if para_start == -1:
                para_start = current_pos
            
            para_end = para_start + len(para)
            
            chunk = self._create_chunk(
                content=para,
                index=len(chunks),
                start_pos=offset + para_start,
                end_pos=offset + para_end,
                chunk_type=ChunkTypeEnum.TEXT.value
            )
            chunks.append(chunk)
            
            current_pos = para_end
        
        return chunks
    
    def get_supported_types(self) -> List[str]:
        """Get list of content types this chunker can extract."""
        types = []
        if self.include_tables:
            types.append(ChunkTypeEnum.TABLE.value)
        if self.include_images:
            types.append(ChunkTypeEnum.IMAGE.value)
        if self.include_code:
            types.append(ChunkTypeEnum.CODE.value)
        if self.text_strategy != 'none':
            types.append(ChunkTypeEnum.TEXT.value)
        return types
