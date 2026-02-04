"""
Document feature analysis service.

Analyzes document content to extract features for model recommendation:
- Language detection
- Domain classification
- Multimodal content detection (binary)

【业界最佳实践】多模态检测采用二值判断:
- 有图片 → 必须使用多模态模型（硬性要求）
- 有表格 → 推荐多模态模型（软性建议）
- 纯文本 → 使用文本模型

参考: LlamaIndex, LangChain, Unstructured.io
- LlamaIndex: 检测到图片 → 用 MultiModalLLM
- LangChain: 按 MIME 类型路由
- Unstructured: 元素类型分类
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..utils.language_detector import LanguageDetector, detect_aggregate_language
from ..utils.domain_classifier import DomainClassifier, classify_aggregate_domain
from ..models.model_recommendation import DocumentAnalysis


# 图片占位符正则模式（支持多种格式）
IMAGE_PLACEHOLDER_PATTERNS = [
    re.compile(r'\[IMAGE_\d+:?\s*[^\]]*\]', re.IGNORECASE),  # [IMAGE_1: Image] 或 [IMAGE_1]
    re.compile(r'\[图片_?\d*\]', re.IGNORECASE),  # [图片] 或 [图片_1]
    re.compile(r'!\[[^\]]*\]\([^)]+\)', re.IGNORECASE),  # Markdown格式 ![alt](url)
    re.compile(r'<img[^>]*>', re.IGNORECASE),  # HTML img标签
]


class DocumentFeatureService:
    """
    Service for analyzing document features.
    
    Extracts features used for intelligent model recommendation:
    - Primary language and distribution
    - Domain classification
    - Multimodal content detection (binary judgment)
    
    【业界最佳实践】二值判断策略:
    - has_images: 是否包含图片（硬性要求多模态）
    - has_tables: 是否包含表格（软性建议多模态）
    - 摒弃复杂的比例计算，采用简单直接的判断逻辑
    """
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.domain_classifier = DomainClassifier()
    
    def _count_image_placeholders(self, content: str) -> int:
        """
        统计文本内容中的图片占位符数量。
        
        支持检测多种图片占位符格式:
        - [IMAGE_1: Image] 或 [IMAGE_1]
        - [图片] 或 [图片_1]
        - ![alt](url) Markdown格式
        - <img> HTML标签
        
        Args:
            content: 文本内容
            
        Returns:
            图片占位符数量
        """
        if not content:
            return 0
        
        image_count = 0
        for pattern in IMAGE_PLACEHOLDER_PATTERNS:
            matches = pattern.findall(content)
            image_count += len(matches)
        
        return image_count
    
    def _has_image_in_metadata(self, metadata: dict) -> bool:
        """
        检查metadata中是否包含图片相关信息。
        
        Args:
            metadata: 分块元数据
            
        Returns:
            是否包含图片信息
        """
        if not metadata:
            return False
        
        # 检查常见的图片相关字段
        image_fields = [
            'has_image', 'has_images', 'image_count', 'images',
            'image_path', 'image_paths', 'base64_data', 'thumbnail_base64',
            'file_path'  # 图片文件路径
        ]
        
        for field in image_fields:
            value = metadata.get(field)
            if value:
                # 对于布尔值或数字，直接判断
                if isinstance(value, bool) and value:
                    return True
                if isinstance(value, (int, float)) and value > 0:
                    return True
                # 对于列表或字符串，判断非空
                if isinstance(value, (list, str)) and len(value) > 0:
                    return True
        
        return False
    
    def analyze_document(
        self,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]]
    ) -> DocumentAnalysis:
        """
        Analyze document features from chunks.
        
        【优化】增强版多模态检测逻辑:
        1. 首先检查 chunk_type 字段
        2. 对于 text 类型分块，额外检测图片占位符
        3. 检查 metadata 中的图片相关字段
        
        Args:
            document_id: Document identifier
            document_name: Document filename
            chunks: List of chunk dicts with 'content', 'chunk_type'
            
        Returns:
            DocumentAnalysis with detected features
        """
        if not chunks:
            return DocumentAnalysis(
                document_id=document_id,
                document_name=document_name,
                primary_language="unknown",
                language_confidence=0.0,
                detected_domain="general",
                domain_confidence=0.5,
                multimodal_ratio=0.0,
                total_chunks=0,
            )
        
        # Extract text content for analysis
        text_contents = []
        text_chunks = 0
        image_chunks = 0
        table_chunks = 0
        code_chunks = 0
        
        # 【新增】额外统计：嵌入在文本中的图片数量（占位符形式）
        embedded_image_count = 0
        
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'text')
            content = chunk.get('content', '')
            metadata = chunk.get('metadata', {})
            
            if chunk_type == 'text':
                text_chunks += 1
                if content:
                    text_contents.append(content)
                    # 【新增】检测文本中的图片占位符
                    placeholder_count = self._count_image_placeholders(content)
                    embedded_image_count += placeholder_count
                
                # 【新增】检测metadata中的图片信息
                if self._has_image_in_metadata(metadata):
                    embedded_image_count += 1
                    
            elif chunk_type == 'image':
                image_chunks += 1
                # Include caption for analysis
                caption = metadata.get('caption', content)
                if caption:
                    text_contents.append(caption)
            elif chunk_type == 'table':
                table_chunks += 1
                if content:
                    text_contents.append(content)
            elif chunk_type == 'code':
                code_chunks += 1
                # Don't include code in language detection
        
        total_chunks = len(chunks)
        
        # Language detection
        language_result = self.language_detector.detect_aggregate(text_contents)
        
        # Domain classification
        domain_result = self.domain_classifier.classify_aggregate(
            text_contents, 
            language_result.language
        )
        
        # 【业界最佳实践】二值判断：简化多模态检测逻辑
        # 统计唯一的多模态元素数量
        total_image_count = image_chunks + embedded_image_count
        total_table_count = table_chunks
        
        # 二值判断标志
        has_images = total_image_count > 0  # 有图片 → 硬性要求多模态
        has_tables = total_table_count > 0  # 有表格 → 软性建议多模态
        
        # multimodal_ratio 保留用于统计展示，但不再用于模型选择决策
        # 采用简单的比例计算，仅供参考
        multimodal_count = total_image_count + total_table_count
        multimodal_ratio = multimodal_count / total_chunks if total_chunks > 0 else 0.0
        multimodal_ratio = min(1.0, multimodal_ratio)
        
        # Build feature vector for similarity comparison
        feature_vector = self._build_feature_vector(
            language_result.all_languages,
            domain_result.all_domains,
            multimodal_ratio
        )
        
        return DocumentAnalysis(
            document_id=document_id,
            document_name=document_name,
            primary_language=language_result.language,
            language_confidence=language_result.confidence,
            detected_domain=domain_result.domain,
            domain_confidence=domain_result.confidence,
            multimodal_ratio=multimodal_ratio,
            total_chunks=total_chunks,
            text_chunks=text_chunks,
            image_chunks=total_image_count,  # 包含嵌入式图片
            table_chunks=table_chunks,
            code_chunks=code_chunks,
            feature_vector=feature_vector,
            # 【新增】二值判断标志
            has_images=has_images,
            has_tables=has_tables,
        )
    
    def analyze_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[DocumentAnalysis]:
        """
        Analyze features for multiple documents.
        
        Args:
            documents: List of dicts with 'document_id', 'document_name', 'chunks'
            
        Returns:
            List of DocumentAnalysis
        """
        results = []
        for doc in documents:
            analysis = self.analyze_document(
                document_id=doc.get('document_id', ''),
                document_name=doc.get('document_name', ''),
                chunks=doc.get('chunks', [])
            )
            results.append(analysis)
        return results
    
    def _build_feature_vector(
        self,
        language_probs: Dict[str, float],
        domain_probs: Dict[str, float],
        multimodal_ratio: float
    ) -> List[float]:
        """
        Build normalized feature vector for similarity comparison.
        
        Vector dimensions:
        - [0-4]: Language probabilities (zh, en, ja, ko, other)
        - [5-11]: Domain probabilities (general, technical, legal, medical, financial, academic, news)
        - [12]: Multimodal ratio
        """
        # Language features (normalized)
        language_features = [
            language_probs.get('zh', 0.0),
            language_probs.get('en', 0.0),
            language_probs.get('ja', 0.0),
            language_probs.get('ko', 0.0),
            sum(v for k, v in language_probs.items() if k not in ['zh', 'en', 'ja', 'ko']),
        ]
        
        # Domain features (normalized)
        domain_features = [
            domain_probs.get('general', 0.0),
            domain_probs.get('technical', 0.0),
            domain_probs.get('legal', 0.0),
            domain_probs.get('medical', 0.0),
            domain_probs.get('financial', 0.0),
            domain_probs.get('academic', 0.0),
            domain_probs.get('news', 0.0),
        ]
        
        # Combine all features
        return language_features + domain_features + [multimodal_ratio]
    
    def calculate_feature_distance(
        self,
        features1: List[float],
        features2: List[float]
    ) -> float:
        """
        Calculate Euclidean distance between feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Distance (0 = identical, higher = more different)
        """
        if len(features1) != len(features2):
            return float('inf')
        
        squared_sum = sum((a - b) ** 2 for a, b in zip(features1, features2))
        return squared_sum ** 0.5


# Global instance
_default_service = None


def get_document_feature_service() -> DocumentFeatureService:
    """Get default document feature service instance."""
    global _default_service
    if _default_service is None:
        _default_service = DocumentFeatureService()
    return _default_service
