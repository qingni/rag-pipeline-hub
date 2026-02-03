"""
Document feature analysis service.

Analyzes document content to extract features for model recommendation:
- Language detection
- Domain classification
- Multimodal content ratio
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..utils.language_detector import LanguageDetector, detect_aggregate_language
from ..utils.domain_classifier import DomainClassifier, classify_aggregate_domain
from ..models.model_recommendation import DocumentAnalysis


class DocumentFeatureService:
    """
    Service for analyzing document features.
    
    Extracts features used for intelligent model recommendation:
    - Primary language and distribution
    - Domain classification
    - Multimodal content statistics
    """
    
    def __init__(self):
        self.language_detector = LanguageDetector()
        self.domain_classifier = DomainClassifier()
    
    def analyze_document(
        self,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]]
    ) -> DocumentAnalysis:
        """
        Analyze document features from chunks.
        
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
        
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'text')
            content = chunk.get('content', '')
            
            if chunk_type == 'text':
                text_chunks += 1
                if content:
                    text_contents.append(content)
            elif chunk_type == 'image':
                image_chunks += 1
                # Include caption for analysis
                caption = chunk.get('metadata', {}).get('caption', content)
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
        
        # Calculate multimodal ratio
        multimodal_count = image_chunks + table_chunks
        multimodal_ratio = multimodal_count / total_chunks if total_chunks > 0 else 0.0
        
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
            image_chunks=image_chunks,
            table_chunks=table_chunks,
            code_chunks=code_chunks,
            feature_vector=feature_vector,
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
