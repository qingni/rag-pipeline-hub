"""
混合分块策略 (Hybrid Chunker)

针对不同内容类型（正文、代码、表格、图片）智能应用最合适的分块策略，
支持自定义各类内容的处理方式和提取阈值。

合并了原先 MultimodalChunker 的功能，统一处理多种内容类型。
"""
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
import logging
from .base_chunker import BaseChunker
from .image_extractor import ImageExtractor
from ...models.chunk_metadata import ChunkTypeEnum, create_chunk_metadata

logger = logging.getLogger(__name__)

# 支持的 Embedding 模型列表（与 SemanticChunker 保持一致）
SUPPORTED_EMBEDDING_MODELS = ['bge-m3', 'qwen3-embedding-8b', 'hunyuan-embedding']


class HybridChunker(BaseChunker):
    """
    混合分块器：针对不同内容类型（正文、代码块、表格、图片）应用最合适的分块策略。
    
    功能特点：
    - 正文：支持语义分块、按段落、按字符、按标题、不分块等多种策略
    - 代码块：支持按行数、按字符、不分块，可设置最小代码行数阈值
    - 表格：支持独立分块或合并到文本，可设置最小表格行数阈值
    - 图片：支持独立提取图片（使用统一的 ImageExtractor）
    
    语义分块时支持的 Embedding 模型：
    - bge-m3: 1024维，8K上下文，多语言，速度快（推荐）
    - qwen3-embedding-8b: 4096维，32K上下文，高精度
    - hunyuan-embedding: 1024维，腾讯混元
    
    图片提取使用统一的 ImageExtractor，确保所有分块策略的图片处理保持一致。
    """
    
    # Regex patterns for content extraction
    TABLE_PATTERN = re.compile(
        r'(\|[^\n]+\|(?:\n\|[-:| ]+\|)?(?:\n\|[^\n]+\|)*)',
        re.MULTILINE
    )
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?\n([\s\S]*?)```',
        re.MULTILINE
    )
    
    def __init__(self, **params):
        """
        初始化混合分块器。
        
        参数说明：
        - text_strategy: 正文分块策略 ('semantic', 'paragraph', 'character', 'heading', 'none')
        - embedding_model: 语义分块的 Embedding 模型 (default: 'bge-m3')
        - use_embedding: 是否启用 Embedding (default: True)
        - code_strategy: 代码分块策略 ('lines', 'character', 'none')
        - table_strategy: 表格处理策略 ('independent', 'merge_with_text')
        - include_images: 是否提取图片 (default: True)
        - include_tables: 是否提取表格 (default: True)
        - include_code: 是否提取代码块 (default: True)
        - min_table_rows: 最小表格行数阈值 (default: 2)
        - min_code_lines: 最小代码行数阈值 (default: 3)
        - image_base_path: 图片路径的基础目录
        """
        super().__init__(**params)
        self._sub_chunkers = {}
        
        # Store embedding params for semantic text chunking
        self._embedding_model = params.get('embedding_model', 'bge-m3')
        self._use_embedding = params.get('use_embedding', True)
        
        # Content extraction flags (merged from multimodal)
        self._include_images = params.get('include_images', True)
        self._include_tables = params.get('include_tables', True)
        self._include_code = params.get('include_code', True)
        
        # Extraction thresholds (merged from multimodal)
        self._min_table_rows = params.get('min_table_rows', 2)
        self._min_code_lines = params.get('min_code_lines', 3)
        
        # Image extraction - NOTE: _image_extractor is initialized in validate_params()
        self._image_base_path = params.get('image_base_path')
        # self._image_extractor 在 validate_params() 中初始化，不要在这里覆盖
    
    def validate_params(self) -> None:
        """
        验证混合分块参数。
        
        Raises:
            ValueError: 参数无效时抛出
        """
        # Text strategy (extended to support 'none' from multimodal)
        text_strategy = self.params.get('text_strategy', 'semantic')
        if text_strategy not in ['semantic', 'paragraph', 'character', 'heading', 'none']:
            raise ValueError(f"Invalid text_strategy: {text_strategy}")
        
        # Code strategy
        code_strategy = self.params.get('code_strategy', 'lines')
        if code_strategy not in ['lines', 'character', 'none']:
            raise ValueError(f"Invalid code_strategy: {code_strategy}")
        
        # Table strategy
        table_strategy = self.params.get('table_strategy', 'independent')
        if table_strategy not in ['independent', 'merge_with_text']:
            raise ValueError(f"Invalid table_strategy: {table_strategy}")
        
        # Validate size parameters
        text_chunk_size = self.params.get('text_chunk_size', 500)
        if not isinstance(text_chunk_size, int) or text_chunk_size < 100:
            raise ValueError("text_chunk_size must be >= 100")
        
        code_chunk_lines = self.params.get('code_chunk_lines', 50)
        if not isinstance(code_chunk_lines, int) or code_chunk_lines < 10:
            raise ValueError("code_chunk_lines must be >= 10")
        
        # Validate threshold parameters (from multimodal)
        min_table_rows = self.params.get('min_table_rows', 2)
        if not isinstance(min_table_rows, int) or min_table_rows < 1:
            raise ValueError("min_table_rows must be >= 1")
        self._min_table_rows = min_table_rows
        
        min_code_lines = self.params.get('min_code_lines', 3)
        if not isinstance(min_code_lines, int) or min_code_lines < 1:
            raise ValueError("min_code_lines must be >= 1")
        self._min_code_lines = min_code_lines
        
        # Content extraction flags
        self._include_images = self.params.get('include_images', True)
        self._include_tables = self.params.get('include_tables', True)
        self._include_code = self.params.get('include_code', True)
        self._image_base_path = self.params.get('image_base_path')
        
        # Initialize unified image extractor if images are enabled
        if self._include_images:
            self._image_extractor = ImageExtractor(
                image_base_path=self._image_base_path,
                include_images=self._include_images
            )
        else:
            self._image_extractor = None
    
    def _get_text_chunker(self):
        """Get or create the text chunker based on configuration."""
        text_strategy = self.params.get('text_strategy', 'semantic')
        
        # Return None if text strategy is 'none'
        if text_strategy == 'none':
            return None
        
        if 'text' not in self._sub_chunkers:
            from . import get_chunker
            
            text_params = {
                'chunk_size': self.params.get('text_chunk_size', 500),
                'overlap': self.params.get('text_overlap', 50),
            }
            
            # Strategy-specific params
            if text_strategy == 'semantic':
                text_params['similarity_threshold'] = self.params.get('similarity_threshold', 0.5)
                text_params['min_chunk_size'] = self.params.get('text_chunk_size', 500)
                text_params['max_chunk_size'] = self.params.get('text_chunk_size', 500) * 3
                # Pass embedding params from HybridChunker
                text_params['use_embedding'] = self._use_embedding
                text_params['embedding_model'] = self._embedding_model
                text_params['embedding_similarity_threshold'] = self.params.get(
                    'embedding_similarity_threshold', 0.7
                )
            elif text_strategy == 'paragraph':
                text_params['min_chunk_size'] = self.params.get('text_chunk_size', 500) // 2
                text_params['max_chunk_size'] = self.params.get('text_chunk_size', 500) * 2
            elif text_strategy == 'heading':
                text_params['min_heading_level'] = self.params.get('min_heading_level', 1)
                text_params['max_heading_level'] = self.params.get('max_heading_level', 3)
            
            self._sub_chunkers['text'] = get_chunker(text_strategy, **text_params)
        
        return self._sub_chunkers['text']
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        使用混合策略对文本进行分块。
        
        对于 Excel 等有页面/工作表结构的文件，每个工作表独立处理，
        确保 sheet_name 正确关联到每个分块。
        
        Args:
            text: 输入文本
            metadata: 可选的文档元数据
                     期望格式: {"pages": [{"page_number": 1, "sheet_name": "xxx", "text": "...", ...}], ...}
        
        Returns:
            包含内容类型标记的分块列表
        """
        if not text or len(text) == 0:
            return []
        
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
        按页面/工作表分块，每个页面作为独立单元处理。
        确保 Excel 工作表边界被正确保留。
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
            is_tsv_table = self._is_tsv_table(page_text)
            
            if is_tsv_table and self._include_tables:
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
                # Process page with standard hybrid extraction
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
        """检查文本是否为 TSV（制表符分隔）格式的表格。"""
        lines = text.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # Check if most lines have tabs (indicating TSV format)
        tab_lines = sum(1 for line in lines if '\t' in line)
        return tab_lines >= len(lines) * 0.5
    
    def _create_tsv_table_chunk(
        self, 
        text: str, 
        offset: int, 
        sheet_name: Optional[str],
        page_number: Optional[int],
        chunk_index: int
    ) -> Dict[str, Any]:
        """从 TSV 格式文本创建表格分块。"""
        lines = text.strip().split('\n')
        
        # Skip "Sheet: xxx" header line if present
        data_lines = [line for line in lines if not line.startswith("Sheet:")]
        
        row_count = len(data_lines)
        col_count = max(len(line.split('\t')) for line in data_lines) if data_lines else 0
        
        # Extract headers
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
        对单个页面进行混合分块。
        所有来自此页面的分块都会继承 sheet_name。
        """
        chunks = []
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract images using unified ImageExtractor
        if self._include_images and self._image_extractor:
            image_chunks, image_regions = self._image_extractor.extract_images(
                text=text,
                metadata=metadata,
                global_offset=global_offset,
                sheet_name=sheet_name,
                page_number=page_number
            )
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract tables
        if self._include_tables:
            table_chunks, table_regions = self._extract_tables_from_page(
                text, global_offset, sheet_name, page_number
            )
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks
        if self._include_code:
            code_chunks, code_regions = self._extract_code_from_page(
                text, global_offset, sheet_name, page_number
            )
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract remaining text (if text strategy is not 'none')
        text_strategy = self.params.get('text_strategy', 'semantic')
        if text_strategy != 'none':
            text_chunks = self._extract_text_from_page(
                text, global_offset, extracted_regions, sheet_name, page_number
            )
            chunks.extend(text_chunks)
        
        return chunks
    
    def _extract_tables_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """从页面中提取 Markdown 表格，并保留上下文信息。"""
        chunks = []
        regions = []
        table_strategy = self.params.get('table_strategy', 'independent')

        # If merge_with_text, don't extract tables separately
        if table_strategy == 'merge_with_text':
            return chunks, regions

        for match in self.TABLE_PATTERN.finditer(text):
            table_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            rows = [r.strip() for r in table_text.split('\n') if r.strip()]
            if len(rows) < self._min_table_rows:
                continue

            # Parse headers
            headers = self._parse_table_headers(rows[0]) if rows else []

            # Check for separator row
            has_separator = len(rows) > 1 and re.match(r'^\|[-:| ]+\|$', rows[1])
            data_row_count = len(rows) - (2 if has_separator else 1)

            # ✨ 提取上下文信息
            section_title, context_before, context_after = self._extract_context(
                text=text,
                start_pos=start_pos,
                end_pos=end_pos,
                context_chars=300
            )

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
                sheet_name=sheet_name,
                # ✨ 添加上下文信息
                context_before=context_before,
                context_after=context_after,
                section_title=section_title
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
    
    def _parse_table_headers(self, header_row: str) -> List[str]:
        """解析 Markdown 表格的表头。"""
        if not header_row:
            return []

        headers = []
        parts = header_row.strip().strip('|').split('|')
        for part in parts:
            header = part.strip()
            if header:
                headers.append(header)

        return headers

    def _extract_context(
        self,
        text: str,
        start_pos: int,
        end_pos: int,
        context_chars: int = 300
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        提取元素前后的上下文文本和所属章节标题。

        Args:
            text: 完整文本
            start_pos: 元素在文本中的起始位置
            end_pos: 元素在文本中的结束位置
            context_chars: 上下文提取的最大字符数

        Returns:
            Tuple of (section_title, context_before, context_after)
            - section_title: 最近的章节标题（## xxx）
            - context_before: 元素前的文本摘要
            - context_after: 元素后的文本摘要
        """
        # 提取章节标题（查找最近的 ## 或 ### 标题）
        text_before = text[:start_pos]
        heading_pattern = r'^(#{1,6})\s+(.+)$'
        lines = text_before.split('\n')
        section_title = None

        # 从后往前查找最近的标题
        for line in reversed(lines):
            match = re.match(heading_pattern, line.strip())
            if match:
                section_title = line.strip()
                break

        # 提取前文上下文（最多 context_chars 字符）
        context_before_start = max(0, start_pos - context_chars)
        context_before = text[context_before_start:start_pos].strip()
        # 尝试在句号处断开，保持句子完整
        if context_before:
            last_period = context_before.rfind('.')
            if last_period > 0 and last_period > len(context_before) * 0.5:
                context_before = context_before[last_period + 1:].strip()

        # 提取后文上下文（最多 context_chars 字符）
        context_after_end = min(len(text), end_pos + context_chars)
        context_after = text[end_pos:context_after_end].strip()
        # 尝试在句号处断开，保持句子完整
        if context_after:
            first_period = context_after.find('.')
            if first_period > 0 and first_period > len(context_after) * 0.3:
                context_after = context_after[:first_period + 1].strip()

        return section_title, context_before, context_after
    
    def _extract_code_from_page(
        self,
        text: str,
        global_offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int, str]]]:
        """从页面中提取代码块，并保留上下文信息。"""
        chunks = []
        regions = []
        code_strategy = self.params.get('code_strategy', 'lines')

        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code_content = match.group(2).strip()
            start_pos = match.start()
            end_pos = match.end()

            lines = code_content.split('\n')
            if len(lines) < self._min_code_lines:
                continue

            # ✨ 提取上下文信息
            section_title, context_before, context_after = self._extract_context(
                text=text,
                start_pos=start_pos,
                end_pos=end_pos,
                context_chars=300
            )

            # If code_strategy is 'none', keep as single chunk
            # Otherwise, we'll process it later in _chunk_code
            if code_strategy == 'none':
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
                    is_complete_block=True,
                    # ✨ 添加上下文信息
                    context_before=context_before,
                    context_after=context_after,
                    section_title=section_title
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
    
    def _extract_text_from_page(
        self,
        text: str,
        global_offset: int,
        extracted_regions: List[Tuple[int, int, str]],
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> List[Dict[str, Any]]:
        """从页面中提取文本分块，排除已提取的区域。"""
        chunks = []
        text_strategy = self.params.get('text_strategy', 'semantic')
        
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
            
            if text_strategy == 'character':
                segment_chunks = self._chunk_text_by_character_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number
                )
            elif text_strategy == 'paragraph':
                segment_chunks = self._chunk_text_by_paragraph_with_sheet(
                    segment_text, global_offset + seg_start, sheet_name, page_number
                )
            else:
                # For semantic/heading, use the sub-chunker
                segment_chunks = self._chunk_text_with_sub_chunker(
                    segment_text, global_offset + seg_start, sheet_name, page_number
                )
            
            chunks.extend(segment_chunks)
        
        return chunks
    
    def _chunk_text_by_character_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> List[Dict[str, Any]]:
        """按字符分块，支持 sheet_name。"""
        chunks = []
        chunk_size = self.params.get('text_chunk_size', 500)
        overlap = self.params.get('text_overlap', 50)
        step = chunk_size - overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + chunk_size]
            if not chunk_text.strip():
                continue
            
            chunk_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TEXT.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=chunk_text,
                start_position=offset + i,
                end_position=offset + i + len(chunk_text)
            )
            
            if sheet_name:
                chunk_metadata['sheet_name'] = sheet_name
            if page_number is not None:
                chunk_metadata['page_number'] = page_number
            
            chunks.append({
                'content': chunk_text,
                'chunk_type': ChunkTypeEnum.TEXT.value,
                'parent_id': None,
                'metadata': chunk_metadata
            })
        
        return chunks
    
    def _chunk_text_by_paragraph_with_sheet(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> List[Dict[str, Any]]:
        """按段落分块，支持 sheet_name。"""
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
            
            chunk_metadata = create_chunk_metadata(
                chunk_type=ChunkTypeEnum.TEXT.value,
                chunk_id=str(uuid.uuid4()),
                chunk_index=len(chunks),
                content=para,
                start_position=offset + para_start,
                end_position=offset + para_end
            )
            
            if sheet_name:
                chunk_metadata['sheet_name'] = sheet_name
            if page_number is not None:
                chunk_metadata['page_number'] = page_number
            
            chunks.append({
                'content': para,
                'chunk_type': ChunkTypeEnum.TEXT.value,
                'parent_id': None,
                'metadata': chunk_metadata
            })
            
            current_pos = para_end
        
        return chunks
    
    def _chunk_text_with_sub_chunker(
        self,
        text: str,
        offset: int,
        sheet_name: Optional[str],
        page_number: Optional[int]
    ) -> List[Dict[str, Any]]:
        """使用子分块器进行分块（语义/标题分块）。"""
        text_chunker = self._get_text_chunker()
        if not text_chunker:
            return []
        
        raw_chunks = text_chunker.chunk(text)
        chunks = []
        
        for raw_chunk in raw_chunks:
            chunk_metadata = raw_chunk.get('metadata', {})
            chunk_metadata['start_position'] = offset + chunk_metadata.get('start_position', 0)
            chunk_metadata['end_position'] = offset + chunk_metadata.get('end_position', len(raw_chunk['content']))
            
            if sheet_name:
                chunk_metadata['sheet_name'] = sheet_name
            if page_number is not None:
                chunk_metadata['page_number'] = page_number
            
            chunks.append({
                'content': raw_chunk['content'],
                'chunk_type': raw_chunk.get('chunk_type', ChunkTypeEnum.TEXT.value),
                'parent_id': raw_chunk.get('parent_id'),
                'metadata': chunk_metadata
            })
        
        return chunks
    
    def _chunk_full_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        对没有页面/工作表结构的文档进行完整文本分块。
        """
        chunks = []
        extracted_regions: List[Tuple[int, int, str]] = []
        
        # Extract images using unified ImageExtractor
        if self._include_images and self._image_extractor:
            image_chunks, image_regions = self._image_extractor.extract_images(
                text=text,
                metadata=metadata,
                global_offset=0
            )
            chunks.extend(image_chunks)
            extracted_regions.extend(image_regions)
        
        # Extract tables
        if self._include_tables:
            table_chunks, table_regions = self._extract_tables_from_page(
                text, 0, None, None
            )
            chunks.extend(table_chunks)
            extracted_regions.extend(table_regions)
        
        # Extract code blocks
        if self._include_code:
            code_chunks, code_regions = self._extract_code_from_page(
                text, 0, None, None
            )
            chunks.extend(code_chunks)
            extracted_regions.extend(code_regions)
        
        # Extract remaining text (if text strategy is not 'none')
        text_strategy = self.params.get('text_strategy', 'semantic')
        if text_strategy != 'none':
            text_chunks = self._extract_text_from_page(
                text, 0, extracted_regions, None, None
            )
            chunks.extend(text_chunks)
        
        # Sort all chunks by position
        chunks.sort(key=lambda c: c['metadata'].get('start_position', 0))
        
        # Reassign sequence numbers
        for idx, chunk in enumerate(chunks):
            chunk['metadata']['chunk_index'] = idx
        
        logger.info(f"Hybrid chunking produced {len(chunks)} chunks")
        return chunks
    
    def get_supported_types(self) -> List[str]:
        """获取此分块器支持的内容类型列表。"""
        types = []
        if self._include_tables:
            types.append(ChunkTypeEnum.TABLE.value)
        if self._include_images:
            types.append(ChunkTypeEnum.IMAGE.value)
        if self._include_code:
            types.append(ChunkTypeEnum.CODE.value)
        text_strategy = self.params.get('text_strategy', 'semantic')
        if text_strategy != 'none':
            types.append(ChunkTypeEnum.TEXT.value)
        return types
