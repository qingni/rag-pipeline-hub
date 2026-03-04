"""Heading-based chunker implementation."""
import re
import logging
from typing import List, Dict, Any
from .base_chunker import BaseChunker
from ...utils.chunking_helpers import HeadingDetector

logger = logging.getLogger(__name__)


class HeadingChunker(BaseChunker):
    """Chunker that splits text by heading structure."""
    
    # 短 chunk 合并的默认阈值（纯内容字符数）
    DEFAULT_MIN_CHUNK_CONTENT_SIZE = 100
    
    def validate_params(self) -> None:
        """
        Validate heading chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        min_level = self.params.get('min_heading_level', 1)
        max_level = self.params.get('max_heading_level', 6)
        
        if not isinstance(min_level, int) or min_level < 1 or min_level > 6:
            raise ValueError("min_heading_level must be between 1 and 6")
        
        if not isinstance(max_level, int) or max_level < 1 or max_level > 6:
            raise ValueError("max_heading_level must be between 1 and 6")
        
        if min_level > max_level:
            raise ValueError("min_heading_level must be <= max_heading_level")
        
        # 验证短 chunk 合并阈值
        min_content_size = self.params.get(
            'min_chunk_content_size', self.DEFAULT_MIN_CHUNK_CONTENT_SIZE
        )
        if not isinstance(min_content_size, int) or min_content_size < 0:
            raise ValueError("min_chunk_content_size must be a non-negative integer")
        if min_content_size > 500:
            raise ValueError("min_chunk_content_size cannot exceed 500")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by headings.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        min_level = self.params.get('min_heading_level', 1)
        max_level = self.params.get('max_heading_level', 6)
        
        if not text or len(text) == 0:
            return []
        
        # Check if document has heading structure
        if not HeadingDetector.has_heading_structure(text, min_headings=2):
            # Fallback to paragraph chunking
            return self._fallback_to_paragraph(text)
        
        # Detect all headings
        all_headings = HeadingDetector.detect_headings(text)
        
        # Filter headings by level
        headings = [
            h for h in all_headings
            if min_level <= h[3] <= max_level
        ]
        
        if not headings:
            # No headings in range, fallback
            return self._fallback_to_paragraph(text)
        
        chunks = []
        chunk_index = 0
        heading_stack = []  # 用于追踪标题层级: [(heading_text, level), ...]
        
        for i, heading in enumerate(headings):
            start_pos, _, heading_text, level = heading
            
            # 更新标题栈 - 维护当前的标题层级路径
            # 弹出所有级别 >= 当前级别的标题（同级或下级）
            while heading_stack and heading_stack[-1][1] >= level:
                heading_stack.pop()
            
            # 构建完整的标题路径（不包含当前标题）
            heading_path = [h[0] for h in heading_stack]
            
            # 获取直接父标题
            parent_heading = heading_stack[-1][0] if heading_stack else None
            
            # 将当前标题加入栈
            heading_stack.append((heading_text, level))
            
            # 完整路径包含当前标题
            full_heading_path = heading_path + [heading_text]
            
            # Find content end (next heading or end of text)
            if i < len(headings) - 1:
                end_pos = headings[i + 1][0]
            else:
                end_pos = len(text)
            
            # Extract content including heading
            content = text[start_pos:end_pos].strip()
            
            if content:
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    strategy="heading",
                    heading_text=heading_text,
                    heading_level=level,
                    heading_path=full_heading_path,    # 完整标题路径
                    parent_heading=parent_heading,      # 直接父标题
                    min_level=min_level,
                    max_level=max_level
                )
                chunks.append(chunk)
                chunk_index += 1
        
        # If no chunks created, fallback
        if not chunks:
            return self._fallback_to_paragraph(text)
        
        # 核心优化：合并短 chunk，消除碎片
        # 借鉴 Unstructured.io 的 combine_text_under_n_chars 思路
        min_content_size = self.params.get(
            'min_chunk_content_size', self.DEFAULT_MIN_CHUNK_CONTENT_SIZE
        )
        if min_content_size > 0:
            chunks = self._merge_short_chunks(chunks, min_content_size)
        
        return chunks
    
    def _get_pure_content_length(self, content: str) -> int:
        """
        计算去掉标题行后的纯内容长度。
        
        Args:
            content: chunk 的完整内容（包含标题行）
        
        Returns:
            去掉所有标题行后的纯文本字符数
        """
        lines = content.split('\n')
        pure_lines = []
        for line in lines:
            stripped = line.strip()
            # 跳过 Markdown 标题行（# 开头）
            if re.match(r'^#{1,6}\s+', stripped):
                continue
            # 跳过空行
            if not stripped:
                continue
            pure_lines.append(stripped)
        return sum(len(line) for line in pure_lines)
    
    def _merge_short_chunks(
        self, chunks: List[Dict[str, Any]], min_content_size: int
    ) -> List[Dict[str, Any]]:
        """
        合并短 chunk，消除碎片。
        
        合并规则：
        1. 短内容 chunk（纯内容 < min_content_size）→ 尝试与相邻 chunk 合并
        2. 向下合并条件：下一个 chunk 的标题是当前 chunk 的子级（level 更大）
        3. 向上合并条件：不满足向下条件时，向上合并到前一个 chunk
        4. 边界保护：绝不跨越同级或更高级别的标题边界向下合并
           例如：## A 不会向下吞并 ## B（同为 h2）
           但 ## B（纯标题）会向下合并 ### B1（子级）
        
        借鉴 Unstructured.io 的 combine_text_under_n_chars 策略：
        短于阈值的章节自动与相邻章节合并，保证最小 chunk 内容量。
        
        Args:
            chunks: 原始 chunk 列表
            min_content_size: 最小纯内容字符数阈值
        
        Returns:
            合并后的 chunk 列表
        """
        if not chunks or len(chunks) <= 1:
            return chunks
        
        merged = []
        i = 0
        merge_count = 0
        
        while i < len(chunks):
            current = chunks[i]
            current_content = current.get('content', '')
            pure_len = self._get_pure_content_length(current_content)
            current_level = current.get('metadata', {}).get('heading_level', 99)
            
            if pure_len < min_content_size and i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                next_level = next_chunk.get('metadata', {}).get('heading_level', 99)
                
                # 边界保护：只允许向下合并子级（next_level > current_level）
                # 例如：## B (level=2) 可以向下合并 ### B1 (level=3)
                # 但不能向下合并 ## C (level=2) 或 # D (level=1)
                can_merge_down = (next_level > current_level)
                
                if can_merge_down:
                    merged_chunk = self._do_merge(current, next_chunk)
                    chunks[i + 1] = merged_chunk
                    merge_count += 1
                    i += 1
                else:
                    # 不能向下合并（遇到同级或更高级标题边界）
                    # 尝试向上合并到前一个 chunk（也需要边界保护）
                    if merged:
                        prev_level = merged[-1].get('metadata', {}).get('heading_level', 99)
                        # 只有当前 chunk 是前一个 chunk 的子级时才向上合并
                        # 例如：### B1 可以向上合并到 ## A，但 ## B 不能向上合并到 ## A
                        if current_level > prev_level:
                            merged[-1] = self._do_merge(merged[-1], current)
                            merge_count += 1
                        else:
                            # 同级或更高级，不合并，保留原样
                            merged.append(current)
                    else:
                        # 第一个 chunk 且不能向下合并，保留原样
                        merged.append(current)
                    i += 1
            elif pure_len < min_content_size and i == len(chunks) - 1 and merged:
                # 最后一个 chunk 太短 → 尝试向上合并（需要边界保护）
                prev_level = merged[-1].get('metadata', {}).get('heading_level', 99)
                if current_level > prev_level:
                    merged[-1] = self._do_merge(merged[-1], current)
                    merge_count += 1
                else:
                    # 同级或更高级，不合并，保留原样
                    merged.append(current)
                i += 1
            else:
                merged.append(current)
                i += 1
        
        # 重新编号 chunk_index
        for idx, chunk in enumerate(merged):
            chunk['metadata']['chunk_index'] = idx
        
        if merge_count > 0:
            logger.info(
                f"HeadingChunker 短 chunk 合并: {len(chunks) + merge_count} → {len(merged)} "
                f"(合并了 {merge_count} 个碎片 chunk, 阈值={min_content_size})"
            )
        
        return merged
    
    def _do_merge(
        self, chunk_a: Dict[str, Any], chunk_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将两个 chunk 合并为一个。
        
        保留 chunk_a 的标题层级信息，将 chunk_b 的内容追加到 chunk_a。
        在 merged_headings 中记录被合并的标题。
        
        Args:
            chunk_a: 前一个 chunk（保留其 heading_path 等元数据）
            chunk_b: 后一个 chunk（内容追加到 chunk_a）
        
        Returns:
            合并后的新 chunk
        """
        content_a = chunk_a.get('content', '')
        content_b = chunk_b.get('content', '')
        merged_content = content_a + '\n\n' + content_b
        
        meta_a = dict(chunk_a.get('metadata', {}))
        meta_b = chunk_b.get('metadata', {})
        
        # 更新内容相关的元数据
        meta_a['char_count'] = len(merged_content)
        meta_a['word_count'] = len(merged_content.split())
        meta_a['end_position'] = meta_b.get('end_position', meta_a.get('end_position', 0))
        
        # 记录被合并的标题
        merged_headings = meta_a.get('merged_headings', []) or []
        heading_b = meta_b.get('heading_text', '')
        if heading_b:
            merged_headings.append(heading_b)
        meta_a['merged_headings'] = merged_headings
        
        # 合并后的 heading_level 取两者中更高级别（数值更小）的，
        # 防止连锁合并跨越同级大标题边界。
        # 例如：### B1 (level=3) 与 ## C (level=2) 合并后，level=2，
        # 这样下次遇到另一个 ## D 时，边界保护会阻止继续合并。
        level_a = meta_a.get('heading_level', 99)
        level_b = meta_b.get('heading_level', 99)
        meta_a['heading_level'] = min(level_a, level_b)
        
        return {
            'content': merged_content,
            'chunk_type': chunk_a.get('chunk_type', 'text'),
            'parent_id': chunk_a.get('parent_id'),
            'metadata': meta_a
        }
    
    def _fallback_to_paragraph(self, text: str) -> List[Dict[str, Any]]:
        """
        Fallback to paragraph-based chunking when no headings found.
        
        Args:
            text: Input text
        
        Returns:
            List of chunk dictionaries with fallback indicator
        """
        from .paragraph_chunker import ParagraphChunker
        
        # Use paragraph chunker with default params
        fallback_chunker = ParagraphChunker(
            min_chunk_size=100,
            max_chunk_size=1000
        )
        
        chunks = fallback_chunker.chunk(text)
        
        # Add fallback indicator to metadata
        for chunk in chunks:
            chunk['metadata']['fallback_strategy'] = 'paragraph'
            chunk['metadata']['fallback_reason'] = 'insufficient_heading_structure'
            chunk['metadata']['original_strategy'] = 'heading'
        
        return chunks
