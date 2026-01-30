"""Document structure analyzer for intelligent chunking recommendation."""
import re
from typing import Dict, Any, List, Optional, Tuple
from ..models.document_features import DocumentFeatures


class DocumentAnalyzer:
    """Analyzes document structure for chunking strategy recommendation.
    
    This analyzer extracts structural features from documents including:
    - Heading hierarchy
    - Paragraph statistics
    - Table and image counts
    - Code block analysis
    - Overall document complexity
    """
    
    # Regex patterns for structure detection
    HEADING_PATTERNS = {
        1: re.compile(r'^#\s+(.+)$', re.MULTILINE),  # H1
        2: re.compile(r'^##\s+(.+)$', re.MULTILINE),  # H2
        3: re.compile(r'^###\s+(.+)$', re.MULTILINE),  # H3
        4: re.compile(r'^####\s+(.+)$', re.MULTILINE),  # H4
        5: re.compile(r'^#####\s+(.+)$', re.MULTILINE),  # H5
        6: re.compile(r'^######\s+(.+)$', re.MULTILINE),  # H6
    }
    
    # HTML heading patterns
    HTML_HEADING_PATTERN = re.compile(r'<h([1-6])[^>]*>.*?</h\1>', re.IGNORECASE | re.DOTALL)
    
    # Table patterns
    MARKDOWN_TABLE_PATTERN = re.compile(r'^\|.*\|$\n^\|[-:\s|]+\|$', re.MULTILINE)
    HTML_TABLE_PATTERN = re.compile(r'<table[^>]*>.*?</table>', re.IGNORECASE | re.DOTALL)
    
    # Image patterns
    MARKDOWN_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
    HTML_IMAGE_PATTERN = re.compile(r'<img[^>]+>', re.IGNORECASE)
    
    # Code block patterns
    FENCED_CODE_PATTERN = re.compile(r'```[\s\S]*?```')
    INDENTED_CODE_PATTERN = re.compile(r'^(?: {4}|\t).*$', re.MULTILINE)
    
    # Log patterns (timestamp at start of line)
    LOG_TIMESTAMP_PATTERN = re.compile(r'^\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}')
    # Alternative log patterns
    LOG_LEVEL_PATTERN = re.compile(r'^(INFO|DEBUG|WARN|ERROR|FATAL|WARNING|TRACE)\s', re.IGNORECASE)
    
    def analyze(
        self, 
        text: str, 
        document_result: Optional[Dict[str, Any]] = None
    ) -> DocumentFeatures:
        """
        Analyze document structure and extract features.
        
        Args:
            text: Document text content
            document_result: Optional document loading result with structured data
        
        Returns:
            DocumentFeatures with extracted characteristics
        """
        features = DocumentFeatures()
        
        if not text:
            return features
        
        # Basic statistics
        features.total_char_count = len(text)
        features.total_word_count = len(text.split())
        
        # Analyze headings
        heading_levels = self._analyze_headings(text)
        features.heading_levels = heading_levels
        features.heading_count = sum(heading_levels.values())
        
        # Analyze paragraphs
        paragraph_stats = self._analyze_paragraphs(text)
        features.paragraph_count = paragraph_stats["count"]
        features.avg_paragraph_length = paragraph_stats["avg_length"]
        features.max_paragraph_length = paragraph_stats["max_length"]
        features.min_paragraph_length = paragraph_stats["min_length"]
        
        # Analyze multimodal content
        if document_result:
            # Use structured data from document loader
            # Support multiple result formats:
            # 1. { content: { tables: [], images: [] } }
            # 2. { tables: [], images: [] }
            # 3. { metadata: { table_count, image_count } }
            content = document_result.get("content", {})
            
            # Try to get from content first
            tables = content.get("tables", [])
            images = content.get("images", [])
            
            # If not in content, try root level
            if not tables:
                tables = document_result.get("tables", [])
            if not images:
                images = document_result.get("images", [])
            
            # If still empty, check metadata for counts
            if not tables and not images:
                metadata = document_result.get("metadata", {})
                features.table_count = metadata.get("table_count", 0)
                features.image_count = metadata.get("image_count", 0)
            else:
                features.table_count = len(tables) if isinstance(tables, list) else 0
                features.image_count = len(images) if isinstance(images, list) else 0
            
            # If still no images detected, fall back to pattern matching on text
            if features.image_count == 0:
                features.image_count = self._count_images(text)
            if features.table_count == 0:
                features.table_count = self._count_tables(text)
        else:
            # Fall back to pattern matching
            features.table_count = self._count_tables(text)
            features.image_count = self._count_images(text)
        
        # Analyze code blocks
        code_stats = self._analyze_code_blocks(text)
        features.code_block_count = code_stats["count"]
        features.code_block_ratio = code_stats["ratio"]
        
        # Determine document characteristics
        features.has_clear_structure = self._has_clear_structure(features)
        features.is_technical_document = self._is_technical_document(features)
        features.is_narrative_document = self._is_narrative_document(features)
        features.is_structured_data = self._is_structured_data(text, document_result)
        features.document_format = self._get_document_format(document_result)
        features.estimated_complexity = self._estimate_complexity(features)
        
        # Analyze text strategy recommendation features (for hybrid chunking)
        text_strategy_features = self._analyze_text_strategy_features(text, features, document_result)
        features.has_table_layout = text_strategy_features["has_table_layout"]
        features.is_flattened_tabular = text_strategy_features["is_flattened_tabular"]
        features.is_log_like = text_strategy_features["is_log_like"]
        features.is_slide_like = text_strategy_features["is_slide_like"]
        features.line_length_uniformity = text_strategy_features["line_length_uniformity"]
        
        return features
    
    def _analyze_headings(self, text: str) -> Dict[int, int]:
        """Count headings at each level."""
        heading_levels = {}
        
        # Count Markdown headings
        for level, pattern in self.HEADING_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                heading_levels[level] = heading_levels.get(level, 0) + len(matches)
        
        # Count HTML headings
        for match in self.HTML_HEADING_PATTERN.finditer(text):
            level = int(match.group(1))
            heading_levels[level] = heading_levels.get(level, 0) + 1
        
        return heading_levels
    
    def _analyze_paragraphs(self, text: str) -> Dict[str, Any]:
        """Analyze paragraph statistics."""
        # Split by double newlines or multiple newlines
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return {"count": 0, "avg_length": 0, "max_length": 0, "min_length": 0}
        
        lengths = [len(p) for p in paragraphs]
        return {
            "count": len(paragraphs),
            "avg_length": sum(lengths) / len(lengths),
            "max_length": max(lengths),
            "min_length": min(lengths)
        }
    
    def _count_tables(self, text: str) -> int:
        """Count tables in text."""
        count = 0
        
        # Count Markdown tables
        count += len(self.MARKDOWN_TABLE_PATTERN.findall(text))
        
        # Count HTML tables
        count += len(self.HTML_TABLE_PATTERN.findall(text))
        
        return count
    
    def _count_images(self, text: str) -> int:
        """Count images in text."""
        count = 0
        
        # Count Markdown images
        count += len(self.MARKDOWN_IMAGE_PATTERN.findall(text))
        
        # Count HTML images
        count += len(self.HTML_IMAGE_PATTERN.findall(text))
        
        return count
    
    def _analyze_code_blocks(self, text: str) -> Dict[str, Any]:
        """Analyze code blocks in text."""
        # Find all code blocks
        fenced_blocks = self.FENCED_CODE_PATTERN.findall(text)
        
        total_code_length = sum(len(block) for block in fenced_blocks)
        code_ratio = total_code_length / len(text) if text else 0
        
        return {
            "count": len(fenced_blocks),
            "ratio": code_ratio
        }
    
    def _has_clear_structure(self, features: DocumentFeatures) -> bool:
        """Determine if document has clear hierarchical structure."""
        # Clear structure = multiple heading levels with reasonable counts
        if features.heading_count < 3:
            return False
        
        # Check if there's a hierarchy
        levels_with_headings = len([l for l, c in features.heading_levels.items() if c > 0])
        return levels_with_headings >= 2
    
    def _is_technical_document(self, features: DocumentFeatures) -> bool:
        """Determine if document is technical (code-heavy, tables, etc.)."""
        return (
            features.code_block_ratio > 0.2 or
            features.code_block_count > 3 or
            features.table_count > 2
        )
    
    def _is_narrative_document(self, features: DocumentFeatures) -> bool:
        """Determine if document is narrative (continuous text, few structures)."""
        return (
            features.heading_count < 3 and
            features.table_count < 2 and
            features.code_block_count < 2 and
            features.avg_paragraph_length > 200
        )
    
    def _is_structured_data(self, text: str, document_result: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if document contains structured data (JSON, key-value pairs, etc.).
        
        Structured data should be chunked by line/paragraph to keep each record intact.
        """
        # Check if loader indicates structured format
        if document_result:
            loader = document_result.get("loader", "")
            metadata = document_result.get("metadata", {})
            doc_format = metadata.get("format", "")
            
            # JSON, CSV, or similar structured formats
            if loader in ("json", "csv") or doc_format in ("json", "csv"):
                return True
            
            # Check for raw_json in metadata (indicates parsed JSON)
            if metadata.get("raw_json"):
                return True
        
        # Heuristic: check if text looks like key-value pairs
        # Pattern: each line is roughly "Key: Value" or "Key = Value"
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) >= 3:
            kv_pattern = re.compile(r'^.{2,50}:\s+.+$')  # "Key: Value" pattern
            kv_count = sum(1 for line in lines if kv_pattern.match(line))
            if kv_count / len(lines) > 0.6:  # More than 60% lines are key-value
                return True
        
        return False
    
    def _get_document_format(self, document_result: Optional[Dict[str, Any]] = None) -> str:
        """Get the original document format.
        
        Priority:
        1. file_format field (explicitly passed original format)
        2. Infer from file_name/filename extension
        3. metadata.format field
        4. loader field (fallback, usually indicates the loader used)
        """
        if not document_result:
            return ""
        
        # 1. Check for explicitly passed file format (highest priority)
        file_format = document_result.get("file_format", "")
        if file_format:
            return file_format.lower()
        
        # 2. Try to infer from filename
        filename = document_result.get("file_name", "") or document_result.get("filename", "")
        if filename:
            import os
            _, ext = os.path.splitext(filename)
            if ext:
                return ext.lstrip(".").lower()
        
        # 3. Check metadata format
        metadata = document_result.get("metadata", {})
        meta_format = metadata.get("format", "") or metadata.get("file_format", "")
        if meta_format:
            return meta_format.lower()
        
        # 4. Fallback to loader type (not ideal, as this is the loader name)
        # Note: loader names like "unstructured", "docling" are not actual file formats
        loader = document_result.get("loader", "")
        # Only return loader if it looks like a file format
        if loader and loader.lower() in ("json", "csv", "txt", "md", "html", "xml"):
            return loader.lower()
        
        return ""
    
    def _estimate_complexity(self, features: DocumentFeatures) -> str:
        """Estimate document complexity."""
        score = 0
        
        # Heading complexity
        if features.heading_count > 10:
            score += 2
        elif features.heading_count > 5:
            score += 1
        
        # Multimodal complexity
        if features.table_count > 5 or features.image_count > 10:
            score += 2
        elif features.table_count > 0 or features.image_count > 0:
            score += 1
        
        # Code complexity
        if features.code_block_ratio > 0.3:
            score += 2
        elif features.code_block_count > 0:
            score += 1
        
        # Size complexity
        if features.total_char_count > 50000:
            score += 1
        
        if score >= 4:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"
    
    def _analyze_text_strategy_features(
        self,
        text: str,
        features: DocumentFeatures,
        document_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze features for recommending text chunking strategy in hybrid mode.
        
        This method detects document characteristics that affect the choice of
        text chunking strategy (semantic, paragraph, heading, etc.).
        
        Returns:
            Dictionary with:
            - has_table_layout: bool - Whether tables retain Markdown layout
            - is_flattened_tabular: bool - Whether tabular data is flattened to text
            - is_log_like: bool - Whether text is log-like (line-by-line records)
            - is_slide_like: bool - Whether content is slide-like (page-independent)
            - line_length_uniformity: float - Uniformity of line lengths (0-1)
        """
        result = {
            "has_table_layout": True,  # Default: assume tables have layout
            "is_flattened_tabular": False,
            "is_log_like": False,
            "is_slide_like": False,
            "line_length_uniformity": 0.0
        }
        
        if not text:
            return result
        
        doc_format = features.document_format.lower() if features.document_format else ""
        
        # Check for actual Markdown table layout in text and document_result
        # Important: table_count > 0 doesn't mean layout is preserved (e.g., unstructured xlsx)
        has_table_layout = False
        
        # 1. Check if document_result tables have actual Markdown layout (| separators)
        if document_result and document_result.get("tables"):
            for table in document_result.get("tables", []):
                markdown = table.get("markdown", "")
                # Real Markdown tables should contain | separators
                if "|" in markdown:
                    has_table_layout = True
                    break
        
        # 2. Check if text itself contains Markdown table format
        if not has_table_layout:
            has_table_layout = bool(self.MARKDOWN_TABLE_PATTERN.search(text))
        
        result["has_table_layout"] = has_table_layout
        
        # Detect flattened tabular data (table format without table layout)
        # For spreadsheet formats, if tables were detected but no layout, it's flattened
        if doc_format in ("xlsx", "xls", "csv") and features.table_count > 0 and not has_table_layout:
            result["is_flattened_tabular"] = True
        else:
            result["is_flattened_tabular"] = self._detect_flattened_tabular(
                text, doc_format, has_table_layout
            )
        
        # Detect log-like text
        result["is_log_like"] = self._detect_log_like_text(text)
        
        # Detect slide-like content (PPT/PPTX)
        result["is_slide_like"] = self._detect_slide_like_content(
            text, doc_format, document_result
        )
        
        # Calculate line length uniformity
        result["line_length_uniformity"] = self._calculate_line_uniformity(text)
        
        return result
    
    def _detect_flattened_tabular(
        self,
        text: str,
        doc_format: str,
        has_markdown_tables: bool
    ) -> bool:
        """
        Detect if text is flattened tabular data (table content without layout).
        
        Characteristics:
        1. Document format is spreadsheet (xlsx/csv) or similar
        2. No Markdown table format in text (| separators)
        3. Lines have uniform length (tabular data pattern)
        """
        # Only check for spreadsheet formats
        if doc_format not in ("xlsx", "xls", "csv"):
            return False
        
        # If Markdown tables exist, layout is preserved
        if has_markdown_tables:
            return False
        
        # Check line pattern characteristics
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) < 3:
            return False
        
        # Check for uniform line lengths (typical of tabular data)
        sample_lines = lines[:min(30, len(lines))]
        lengths = [len(line) for line in sample_lines]
        avg_len = sum(lengths) / len(lengths)
        
        if avg_len < 20:  # Too short, unlikely to be tabular
            return False
        
        # Calculate coefficient of variation (CV)
        if avg_len > 0:
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            std_dev = variance ** 0.5
            cv = std_dev / avg_len
            
            # Low CV (< 0.5) indicates uniform line lengths -> likely flattened table
            if cv < 0.5:
                return True
        
        return False
    
    def _detect_log_like_text(self, text: str) -> bool:
        """
        Detect if text is log-like (timestamps, log levels, line-by-line records).
        
        Log files should be chunked by paragraph to keep each log entry intact.
        """
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) < 5:
            return False
        
        sample_lines = lines[:min(30, len(lines))]
        
        # Check for timestamp patterns at line start
        timestamp_count = sum(
            1 for line in sample_lines 
            if self.LOG_TIMESTAMP_PATTERN.match(line)
        )
        
        # Check for log level patterns
        log_level_count = sum(
            1 for line in sample_lines
            if self.LOG_LEVEL_PATTERN.match(line)
        )
        
        total_matches = timestamp_count + log_level_count
        match_ratio = total_matches / len(sample_lines) if sample_lines else 0
        
        # If more than 40% of lines have log patterns, consider it log-like
        return match_ratio > 0.4
    
    def _detect_slide_like_content(
        self,
        text: str,
        doc_format: str,
        document_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Detect if content is slide-like (PPT/PPTX characteristics).
        
        Slide content should be chunked by paragraph to keep each slide intact.
        
        Characteristics:
        1. Document format is pptx/ppt
        2. Short paragraphs with clear separations
        3. Bullet point style content
        
        Note: Different document formats use different thresholds to avoid
        misclassifying bullet-point-heavy Word documents as slide-like.
        """
        fmt = doc_format.lower() if doc_format else ""
        
        # Direct format check - PPT files are always slide-like
        if fmt in ("pptx", "ppt"):
            return True
        
        # Check metadata for slide indicators
        if document_result:
            metadata = document_result.get("metadata", {})
            if metadata.get("slide_count", 0) > 0:
                return True
            if metadata.get("format", "").lower() in ("pptx", "ppt"):
                return True
        
        # Heuristic: check for slide-like text patterns
        # Short paragraphs, many bullet points
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if len(paragraphs) < 3:
            return False
        
        # Check average paragraph length (slides have short paragraphs)
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
        
        # Check for bullet point patterns
        bullet_pattern = re.compile(r'^[\s]*[-•*▪▸►]\s')
        bullet_lines = sum(
            1 for p in paragraphs 
            for line in p.split('\n') 
            if bullet_pattern.match(line)
        )
        total_lines = sum(len(p.split('\n')) for p in paragraphs)
        bullet_ratio = bullet_lines / total_lines if total_lines > 0 else 0
        
        # Use different thresholds based on document format
        # Word documents (docx/doc): stricter thresholds to avoid misclassifying
        # bullet-point-heavy documents as slide-like
        if fmt in ("docx", "doc"):
            # Only very short paragraphs (<100) + very high bullet ratio (>0.6)
            # indicates true slide-like content in Word
            return avg_para_len < 100 and bullet_ratio > 0.6
        else:
            # Other formats: use standard thresholds
            # Short paragraphs + high bullet ratio = slide-like
            return avg_para_len < 300 and bullet_ratio > 0.3
    
    def _calculate_line_uniformity(self, text: str) -> float:
        """
        Calculate line length uniformity (0-1, higher = more uniform).
        
        Uniform line lengths indicate structured/tabular data.
        """
        lines = [l for l in text.split('\n') if l.strip()]
        if len(lines) < 3:
            return 0.0
        
        sample_lines = lines[:min(50, len(lines))]
        lengths = [len(line) for line in sample_lines]
        avg_len = sum(lengths) / len(lengths)
        
        if avg_len < 10:
            return 0.0
        
        # Calculate coefficient of variation
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        std_dev = variance ** 0.5
        cv = std_dev / avg_len if avg_len > 0 else 1.0
        
        # Convert CV to uniformity score (lower CV = higher uniformity)
        # CV of 0 -> uniformity of 1.0
        # CV of 1 -> uniformity of 0.0
        uniformity = max(0.0, min(1.0, 1.0 - cv))
        return round(uniformity, 3)


# Singleton instance
_analyzer_instance = None


def get_document_analyzer() -> DocumentAnalyzer:
    """Get the document analyzer singleton instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = DocumentAnalyzer()
    return _analyzer_instance


def analyze_document(
    text: str, 
    document_result: Optional[Dict[str, Any]] = None
) -> DocumentFeatures:
    """Convenience function to analyze document features."""
    analyzer = get_document_analyzer()
    return analyzer.analyze(text, document_result)
