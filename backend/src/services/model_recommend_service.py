"""
Intelligent model recommendation service.

Recommends the best embedding model based on document features:
- Language matching
- Domain expertise
- Multimodal support

Uses weighted scoring algorithm:
Total Score = Language × 40% + Domain × 35% + Multimodal × 25%
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..models.model_recommendation import (
    ModelScore,
    DimensionScore,
    ModelRecommendation,
    RecommendationReason,
    RecommendationConfidence,
    DocumentAnalysis,
    SingleRecommendationResult,
    BatchRecommendationResult,
    BatchFeatureSummary,
    OutlierDocument,
)
from .model_capability_service import (
    ModelCapabilityService,
    ModelCapabilityInfo,
    get_model_capability_service,
)
from .document_feature_service import (
    DocumentFeatureService,
    get_document_feature_service,
)


class ModelRecommendService:
    """
    Intelligent model recommendation engine.
    
    Analyzes document features and recommends the best embedding model
    using a weighted scoring algorithm.
    """
    
    def __init__(
        self,
        capability_service: Optional[ModelCapabilityService] = None,
        feature_service: Optional[DocumentFeatureService] = None,
    ):
        """
        Initialize service.
        
        Args:
            capability_service: Model capability service (optional)
            feature_service: Document feature service (optional)
        """
        self.capability_service = capability_service or get_model_capability_service()
        self.feature_service = feature_service or get_document_feature_service()
    
    def recommend_for_document(
        self,
        document_analysis: DocumentAnalysis,
        top_n: int = 3,
    ) -> SingleRecommendationResult:
        """
        Recommend models for a single document.
        
        Args:
            document_analysis: Analyzed document features
            top_n: Number of top recommendations
            
        Returns:
            SingleRecommendationResult with ranked recommendations
        """
        # Get all enabled models
        models = self.capability_service.get_all_models(enabled_only=True)
        
        if not models:
            # Return default recommendation
            return self._default_recommendation(document_analysis)
        
        # Score each model
        scored_models = []
        for model in models:
            score = self._score_model(model, document_analysis)
            scored_models.append(score)
        
        # Sort by total score (descending)
        scored_models.sort(key=lambda x: x.total_score, reverse=True)
        
        # Build recommendations
        recommendations = []
        for rank, model_score in enumerate(scored_models[:top_n], 1):
            confidence = self._calculate_confidence(model_score.total_score)
            reasons = self._generate_reasons(model_score, document_analysis)
            
            recommendations.append(ModelRecommendation(
                rank=rank,
                model=model_score,
                confidence=confidence,
                reasons=reasons,
            ))
        
        return SingleRecommendationResult(
            document_analysis=document_analysis,
            recommendations=recommendations,
            top_recommendation=recommendations[0] if recommendations else None,
        )
    
    def recommend_for_chunks(
        self,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]],
        top_n: int = 3,
    ) -> SingleRecommendationResult:
        """
        Analyze document and recommend models.
        
        Convenience method that combines analysis and recommendation.
        
        Args:
            document_id: Document identifier
            document_name: Document filename
            chunks: List of chunk dicts
            top_n: Number of recommendations
            
        Returns:
            SingleRecommendationResult
        """
        # Analyze document
        analysis = self.feature_service.analyze_document(
            document_id, document_name, chunks
        )
        
        # Get recommendations
        return self.recommend_for_document(analysis, top_n)
    
    def recommend_for_batch(
        self,
        documents: List[Dict[str, Any]],
        top_n: int = 3,
        outlier_threshold: Optional[float] = None,
    ) -> BatchRecommendationResult:
        """
        Recommend model for a batch of documents.
        
        Analyzes all documents, provides unified recommendation,
        and flags outlier documents.
        
        Args:
            documents: List of dicts with 'document_id', 'document_name', 'chunks'
            top_n: Number of recommendations
            outlier_threshold: Threshold for outlier detection (default from config)
            
        Returns:
            BatchRecommendationResult with unified recommendation and outliers
        """
        if not documents:
            return self._empty_batch_result()
        
        # Use default threshold if not specified
        if outlier_threshold is None:
            outlier_threshold = self.capability_service.get_outlier_threshold()
        
        # Analyze all documents
        analyses = self.feature_service.analyze_documents_batch(documents)
        
        # Calculate aggregate features
        feature_summary = self._calculate_batch_summary(analyses)
        
        # Create synthetic document analysis from aggregate
        aggregate_analysis = self._create_aggregate_analysis(feature_summary)
        
        # Get unified recommendation
        unified_result = self.recommend_for_document(aggregate_analysis, top_n)
        
        # Detect outliers
        outliers = self._detect_outliers(analyses, feature_summary, outlier_threshold)
        
        return BatchRecommendationResult(
            feature_summary=feature_summary,
            unified_recommendation=unified_result.recommendations,
            outlier_documents=outliers,
            document_analyses=analyses,
            outlier_threshold=outlier_threshold,
        )
    
    def _score_model(
        self,
        model: ModelCapabilityInfo,
        analysis: DocumentAnalysis,
    ) -> ModelScore:
        """
        Score a model for given document features.
        
        Uses weighted scoring:
        - Language: 40%
        - Domain: 35%
        - Multimodal: 25%
        """
        weights = self.capability_service.get_recommendation_weights()
        
        # Calculate language score
        language_score = model.language_scores.get_score(analysis.primary_language)
        # Adjust by confidence
        language_score *= (0.5 + 0.5 * analysis.language_confidence)
        
        # Calculate domain score
        domain_score = model.domain_scores.get_score(analysis.detected_domain)
        # Adjust by confidence
        domain_score *= (0.5 + 0.5 * analysis.domain_confidence)
        
        # Calculate multimodal score
        if analysis.multimodal_ratio > 0:
            # Document has multimodal content
            multimodal_score = model.multimodal_score
            # Boost score if model supports multimodal
            if multimodal_score > 0.5:
                multimodal_score *= (1 + analysis.multimodal_ratio * 0.5)
            else:
                # Penalize text-only models for multimodal content
                multimodal_score = max(0.3, 1.0 - analysis.multimodal_ratio)
        else:
            # No multimodal content - all models equally suitable
            multimodal_score = 0.8
        
        # Calculate weighted total
        dimension_scores = [
            DimensionScore(
                dimension='language',
                score=language_score,
                weight=weights.get('language_match', 0.40),
                weighted_score=language_score * weights.get('language_match', 0.40),
            ),
            DimensionScore(
                dimension='domain',
                score=domain_score,
                weight=weights.get('domain_match', 0.35),
                weighted_score=domain_score * weights.get('domain_match', 0.35),
            ),
            DimensionScore(
                dimension='multimodal',
                score=multimodal_score,
                weight=weights.get('multimodal_support', 0.25),
                weighted_score=multimodal_score * weights.get('multimodal_support', 0.25),
            ),
        ]
        
        total_score = sum(d.weighted_score for d in dimension_scores)
        
        return ModelScore(
            model_name=model.model_name,
            display_name=model.display_name,
            total_score=total_score,
            dimension_scores=dimension_scores,
            language_score=language_score,
            domain_score=domain_score,
            multimodal_score=multimodal_score,
            model_type=model.model_type,
            dimension=model.dimension,
            provider=model.provider,
        )
    
    def _calculate_confidence(self, score: float) -> RecommendationConfidence:
        """Calculate confidence level from score."""
        if score >= 0.8:
            return RecommendationConfidence.HIGH
        elif score >= 0.5:
            return RecommendationConfidence.MEDIUM
        else:
            return RecommendationConfidence.LOW
    
    def _generate_reasons(
        self,
        model_score: ModelScore,
        analysis: DocumentAnalysis,
    ) -> List[RecommendationReason]:
        """Generate human-readable recommendation reasons."""
        reasons = []
        
        # Language reason
        if model_score.language_score >= 0.9:
            reasons.append(RecommendationReason(
                key='language_excellent',
                description=f'对{analysis.primary_language}语言支持出色',
                impact='positive',
            ))
        elif model_score.language_score >= 0.7:
            reasons.append(RecommendationReason(
                key='language_good',
                description=f'对{analysis.primary_language}语言有良好支持',
                impact='positive',
            ))
        elif model_score.language_score < 0.5:
            reasons.append(RecommendationReason(
                key='language_weak',
                description=f'对{analysis.primary_language}语言支持较弱',
                impact='negative',
            ))
        
        # Domain reason
        if model_score.domain_score >= 0.85:
            reasons.append(RecommendationReason(
                key='domain_expert',
                description=f'在{analysis.detected_domain}领域有专长',
                impact='positive',
            ))
        elif model_score.domain_score >= 0.7:
            reasons.append(RecommendationReason(
                key='domain_capable',
                description=f'能够处理{analysis.detected_domain}领域内容',
                impact='positive',
            ))
        
        # Multimodal reason
        if analysis.multimodal_ratio > 0.1:
            if model_score.multimodal_score >= 0.8:
                reasons.append(RecommendationReason(
                    key='multimodal_support',
                    description='支持多模态内容（图片、表格）向量化',
                    impact='positive',
                ))
            elif model_score.multimodal_score < 0.5:
                reasons.append(RecommendationReason(
                    key='multimodal_limited',
                    description='对多模态内容支持有限，将使用文本描述',
                    impact='negative',
                ))
        
        return reasons
    
    def _calculate_batch_summary(
        self,
        analyses: List[DocumentAnalysis],
    ) -> BatchFeatureSummary:
        """Calculate aggregate features for batch."""
        if not analyses:
            return BatchFeatureSummary(document_count=0)
        
        # Language distribution
        language_counts = {}
        for a in analyses:
            lang = a.primary_language
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # Domain distribution
        domain_counts = {}
        for a in analyses:
            domain = a.detected_domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Calculate uniformity (1 - entropy normalized)
        def calculate_uniformity(counts: Dict[str, int]) -> float:
            total = sum(counts.values())
            if total == 0:
                return 0.0
            max_count = max(counts.values())
            return max_count / total
        
        # Multimodal statistics
        total_chunks = sum(a.total_chunks for a in analyses)
        total_image_chunks = sum(a.image_chunks for a in analyses)
        total_table_chunks = sum(a.table_chunks for a in analyses)
        multimodal_ratios = [a.multimodal_ratio for a in analyses]
        avg_multimodal = sum(multimodal_ratios) / len(multimodal_ratios) if multimodal_ratios else 0.0
        
        # Primary language/domain
        primary_language = max(language_counts, key=language_counts.get) if language_counts else 'unknown'
        primary_domain = max(domain_counts, key=domain_counts.get) if domain_counts else 'general'
        
        return BatchFeatureSummary(
            document_count=len(analyses),
            language_distribution=language_counts,
            primary_language=primary_language,
            language_uniformity=calculate_uniformity(language_counts),
            domain_distribution=domain_counts,
            primary_domain=primary_domain,
            domain_uniformity=calculate_uniformity(domain_counts),
            avg_multimodal_ratio=avg_multimodal,
            total_chunks=total_chunks,
            total_image_chunks=total_image_chunks,
            total_table_chunks=total_table_chunks,
        )
    
    def _create_aggregate_analysis(
        self,
        summary: BatchFeatureSummary,
    ) -> DocumentAnalysis:
        """Create synthetic analysis from batch summary."""
        return DocumentAnalysis(
            document_id='__batch__',
            document_name='批量文档',
            primary_language=summary.primary_language,
            language_confidence=summary.language_uniformity,
            detected_domain=summary.primary_domain,
            domain_confidence=summary.domain_uniformity,
            multimodal_ratio=summary.avg_multimodal_ratio,
            total_chunks=summary.total_chunks,
            image_chunks=summary.total_image_chunks,
            table_chunks=summary.total_table_chunks,
        )
    
    def _detect_outliers(
        self,
        analyses: List[DocumentAnalysis],
        summary: BatchFeatureSummary,
        threshold: float,
    ) -> List[OutlierDocument]:
        """Detect documents that deviate significantly from batch average."""
        if len(analyses) < 2:
            return []
        
        outliers = []
        
        # Calculate average feature vector
        if not analyses[0].feature_vector:
            return []
        
        avg_vector = [0.0] * len(analyses[0].feature_vector)
        for analysis in analyses:
            for i, v in enumerate(analysis.feature_vector):
                avg_vector[i] += v
        avg_vector = [v / len(analyses) for v in avg_vector]
        
        # Check each document
        for analysis in analyses:
            distance = self.feature_service.calculate_feature_distance(
                analysis.feature_vector, avg_vector
            )
            
            if distance > threshold:
                reason = self._explain_outlier(analysis, summary)
                outliers.append(OutlierDocument(
                    document_id=analysis.document_id,
                    document_name=analysis.document_name,
                    deviation_score=distance,
                    deviation_reason=reason,
                    suggested_action='建议单独选择模型或确认后继续',
                ))
        
        return outliers
    
    def _explain_outlier(
        self,
        analysis: DocumentAnalysis,
        summary: BatchFeatureSummary,
    ) -> str:
        """Generate explanation for why document is an outlier."""
        reasons = []
        
        # Check language difference
        if analysis.primary_language != summary.primary_language:
            reasons.append(f'语言不同（{analysis.primary_language} vs 主要{summary.primary_language}）')
        
        # Check domain difference
        if analysis.detected_domain != summary.primary_domain:
            reasons.append(f'领域不同（{analysis.detected_domain} vs 主要{summary.primary_domain}）')
        
        # Check multimodal difference
        if abs(analysis.multimodal_ratio - summary.avg_multimodal_ratio) > 0.3:
            if analysis.multimodal_ratio > summary.avg_multimodal_ratio:
                reasons.append('多模态内容比例较高')
            else:
                reasons.append('多模态内容比例较低')
        
        return '；'.join(reasons) if reasons else '特征分布与其他文档差异较大'
    
    def _default_recommendation(
        self,
        analysis: DocumentAnalysis,
    ) -> SingleRecommendationResult:
        """Return default recommendation when no models available."""
        default_model = self.capability_service.get_default_model(
            has_multimodal=analysis.multimodal_ratio > 0.1
        )
        
        return SingleRecommendationResult(
            document_analysis=analysis,
            recommendations=[
                ModelRecommendation(
                    rank=1,
                    model=ModelScore(
                        model_name=default_model,
                        display_name=default_model,
                        total_score=0.7,
                        language_score=0.7,
                        domain_score=0.7,
                        multimodal_score=0.7,
                    ),
                    confidence=RecommendationConfidence.MEDIUM,
                    reasons=[RecommendationReason(
                        key='default',
                        description='使用默认推荐模型',
                        impact='neutral',
                    )],
                )
            ],
            top_recommendation=None,
        )
    
    def _empty_batch_result(self) -> BatchRecommendationResult:
        """Return empty batch result."""
        return BatchRecommendationResult(
            feature_summary=BatchFeatureSummary(document_count=0),
            unified_recommendation=[],
        )


# Global instance
_default_service = None


def get_model_recommend_service() -> ModelRecommendService:
    """Get default model recommend service instance."""
    global _default_service
    if _default_service is None:
        _default_service = ModelRecommendService()
    return _default_service
