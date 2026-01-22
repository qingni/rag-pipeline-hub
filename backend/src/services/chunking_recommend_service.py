"""Chunking recommendation service for intelligent strategy selection."""
import time
from typing import Dict, Any, List, Optional
from ..models.document_features import DocumentFeatures
from ..models.chunking_recommendation import (
    ChunkingRecommendation,
    RecommendationResult,
    get_strategy_display_name
)
from ..models.chunking_task import StrategyType
from ..utils.document_analyzer import analyze_document, get_document_analyzer


class ChunkingRecommendService:
    """Service for recommending optimal chunking strategies.
    
    Uses a rule-based engine to analyze document features and
    recommend the most suitable chunking strategies.
    """
    
    # Default chunk size estimates for each strategy
    DEFAULT_CHUNK_SIZES = {
        StrategyType.CHARACTER: 500,
        StrategyType.PARAGRAPH: 800,
        StrategyType.HEADING: 1500,
        StrategyType.SEMANTIC: 1000,
        StrategyType.PARENT_CHILD: 400,  # Child chunk size
        StrategyType.HYBRID: 800,
        StrategyType.MULTIMODAL: 1000
    }
    
    # Default parameters for each strategy
    DEFAULT_PARAMS = {
        StrategyType.CHARACTER: {"chunk_size": 500, "overlap": 50},
        StrategyType.PARAGRAPH: {"min_chunk_size": 200, "max_chunk_size": 1500},
        StrategyType.HEADING: {"min_heading_level": 1, "max_heading_level": 3},
        StrategyType.SEMANTIC: {"similarity_threshold": 0.3, "min_chunk_size": 300, "max_chunk_size": 1200},
        StrategyType.PARENT_CHILD: {"parent_size": 2000, "child_size": 400, "child_overlap": 50},
        StrategyType.HYBRID: {},
        StrategyType.MULTIMODAL: {"include_tables": True, "include_images": True, "text_strategy": "semantic"}
    }
    
    def __init__(self):
        self.analyzer = get_document_analyzer()
    
    def analyze_document(
        self, 
        text: str, 
        document_result: Optional[Dict[str, Any]] = None
    ) -> DocumentFeatures:
        """Analyze document structure."""
        return self.analyzer.analyze(text, document_result)
    
    def recommend(
        self,
        text: str,
        document_id: str,
        document_result: Optional[Dict[str, Any]] = None,
        top_n: int = 3
    ) -> RecommendationResult:
        """
        Generate chunking strategy recommendations.
        
        Args:
            text: Document text content
            document_id: Document identifier
            document_result: Optional document loading result
            top_n: Number of recommendations to return
        
        Returns:
            RecommendationResult with features and recommendations
        """
        start_time = time.time()
        
        # Analyze document features
        features = self.analyze_document(text, document_result)
        
        # Generate recommendations using rule engine
        recommendations = self._apply_rules(features, text)
        
        # Sort by confidence and limit to top_n
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        # Mark top recommendation and assign ranks
        for i, rec in enumerate(recommendations[:top_n]):
            rec.rank = i + 1
            rec.is_top = (i == 0)
        
        analysis_time = (time.time() - start_time) * 1000
        
        return RecommendationResult(
            document_id=document_id,
            features=features.to_dict(),
            recommendations=recommendations[:top_n],
            analysis_time_ms=analysis_time
        )
    
    def _apply_rules(self, features: DocumentFeatures, text: str) -> List[ChunkingRecommendation]:
        """Apply recommendation rules based on document features.
        
        优先级设计原则：
        0. 结构化数据（JSON/CSV）-> 段落分块（保持每条记录完整）
        1. 多模态内容 -> 多模态分块（图片/表格是独立信息单元）
        2. 清晰标题结构 -> 标题分块（天然语义边界）
        3. 技术文档含代码 -> 混合分块（代码需要特殊处理）
        4. 长篇纯文本无结构 -> 父子分块（精确检索+完整上下文）
        5. 连续叙事文本 -> 语义分块（识别自然边界）
        6. 简单短文档 -> 字符分块（降级策略）
        """
        recommendations = []
        
        # Rule 0: Structured data (JSON/CSV) -> Paragraph chunking (最高优先级)
        # 结构化数据每行是一条完整记录，应按行/段落分块
        if features.is_structured_data:
            rec = self._create_paragraph_recommendation(features)
            rec.confidence = 0.95  # 最高置信度
            rec.reason = f"检测到结构化数据格式（{features.document_format or 'key-value'}），每行是独立的信息单元，按段落分块可保持记录完整性"
            recommendations.append(rec)
        
        # 检测多模态内容
        has_multimodal = features.table_count >= 1 or features.image_count >= 1
        has_rich_multimodal = features.table_count >= 3 or features.image_count >= 3
        
        # Rule 1: Multimodal content -> Multimodal chunking
        # 只要包含图片或表格就推荐，因为图片/表格是独立的信息单元
        if has_multimodal:
            rec = self._create_multimodal_recommendation(features)
            # 根据多模态内容数量调整置信度
            if has_rich_multimodal:
                rec.confidence = 0.92
            elif features.table_count >= 2 or features.image_count >= 2:
                rec.confidence = 0.88
            else:
                rec.confidence = 0.85
            recommendations.append(rec)
        
        # Rule 2: Clear heading structure -> Heading chunking
        if features.has_clear_structure and features.heading_count >= 5:
            rec = self._create_heading_recommendation(features)
            recommendations.append(rec)
        
        # Rule 3: Technical document with code -> Hybrid chunking
        if features.is_technical_document and features.code_block_ratio > 0.2:
            rec = self._create_hybrid_recommendation(features)
            recommendations.append(rec)
        
        # Rule 4: Long narrative -> Semantic chunking
        # 结构化数据不适合语义分块
        if not features.is_structured_data and (features.is_narrative_document or (features.heading_count < 3 and features.total_char_count > 5000)):
            rec = self._create_semantic_recommendation(features)
            recommendations.append(rec)
        
        # Rule 5: Parent-child chunking (严格条件)
        # 只在以下所有条件同时满足时才推荐父子文档：
        # - 文档足够长（>10000字符）
        # - 无多模态内容（图片/表格应独立分块）
        # - 无明确标题结构（有标题应用标题分块）
        # - 非技术文档（代码文档用hybrid）
        # - 非结构化数据
        should_recommend_parent_child = (
            features.total_char_count > 10000 and
            not has_multimodal and
            not features.has_clear_structure and
            features.heading_count < 5 and
            not (features.is_technical_document and features.code_block_ratio > 0.2) and
            not features.is_structured_data
        )
        
        if should_recommend_parent_child:
            rec = self._create_parent_child_recommendation(features)
            rec.confidence = 0.78  # 适中的置信度
            rec.reason = "文档较长且内容连续无明显结构，父子分块可兼顾检索精度和上下文完整性"
            recommendations.append(rec)
        
        # Rule 6: Simple short document -> Character chunking (fallback)
        if features.total_char_count < 5000 or features.estimated_complexity == "low":
            rec = self._create_character_recommendation(features)
            recommendations.append(rec)
        
        # Always add semantic as a baseline option if not already added (except for structured data)
        if not features.is_structured_data and not any(r.strategy == StrategyType.SEMANTIC for r in recommendations):
            rec = self._create_semantic_recommendation(features, baseline=True)
            recommendations.append(rec)
        
        return recommendations
    
    def _create_heading_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for heading-based chunking."""
        heading_summary = features.get_heading_summary()
        
        return ChunkingRecommendation(
            strategy=StrategyType.HEADING,
            strategy_name=get_strategy_display_name(StrategyType.HEADING),
            reason=f"检测到清晰的标题层级结构（{heading_summary}）",
            confidence=0.9 if features.heading_count > 10 else 0.8,
            estimated_chunks=self._estimate_chunks(features, StrategyType.HEADING),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.HEADING],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.HEADING],
            pros=["保持章节完整性", "语义边界清晰", "适合检索问答"],
            cons=["块大小不均匀", "依赖文档结构质量"]
        )
    
    def _create_multimodal_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for multimodal chunking."""
        multimodal_summary = features.get_multimodal_summary()
        
        # 根据多模态内容数量生成不同的推荐理由
        if features.image_count >= 3 or features.table_count >= 3:
            reason = f"文档包含丰富的多模态内容（{multimodal_summary}），图片/表格作为独立信息单元需要独立分块检索"
        elif features.image_count >= 1 and features.table_count >= 1:
            reason = f"文档同时包含图片和表格（{multimodal_summary}），多模态分块可分别独立检索"
        elif features.image_count >= 1:
            reason = f"文档包含图片内容（{multimodal_summary}），图片是完整的视觉信息单元，应独立分块"
        else:
            reason = f"文档包含表格内容（{multimodal_summary}），表格是结构化数据单元，应独立分块"
        
        return ChunkingRecommendation(
            strategy=StrategyType.MULTIMODAL,
            strategy_name=get_strategy_display_name(StrategyType.MULTIMODAL),
            reason=reason,
            confidence=0.85,  # 初始置信度，会在 _apply_rules 中根据数量调整
            estimated_chunks=self._estimate_chunks(features, StrategyType.MULTIMODAL),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.MULTIMODAL],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.MULTIMODAL],
            pros=["图片/表格独立检索", "支持多模态向量化", "内容类型区分清晰"],
            cons=["需要多模态 Embedding 模型", "处理复杂度较高"]
        )
    
    def _create_hybrid_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for hybrid chunking."""
        return ChunkingRecommendation(
            strategy=StrategyType.HYBRID,
            strategy_name=get_strategy_display_name(StrategyType.HYBRID),
            reason=f"检测到技术文档特征（代码占比 {features.code_block_ratio:.1%}），建议混合策略",
            confidence=0.82,
            estimated_chunks=self._estimate_chunks(features, StrategyType.HYBRID),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.HYBRID],
            suggested_params={
                "text": {"strategy": "semantic", "params": {"similarity_threshold": 0.3}},
                "code": {"strategy": "line", "params": {"lines_per_chunk": 50}},
                "table": {"strategy": "independent"},
                "image": {"strategy": "independent"}
            },
            pros=["各类内容针对性处理", "代码保持完整性", "文本语义分块"],
            cons=["配置复杂度高", "需要理解各策略参数"]
        )
    
    def _create_semantic_recommendation(
        self, 
        features: DocumentFeatures,
        baseline: bool = False
    ) -> ChunkingRecommendation:
        """Create recommendation for semantic chunking."""
        if baseline:
            reason = "语义分块是通用策略，适合大多数文档类型"
            confidence = 0.7
        else:
            reason = "检测到连续叙事文本，无明显标题结构，语义分块可识别自然边界"
            confidence = 0.85
        
        return ChunkingRecommendation(
            strategy=StrategyType.SEMANTIC,
            strategy_name=get_strategy_display_name(StrategyType.SEMANTIC),
            reason=reason,
            confidence=confidence,
            estimated_chunks=self._estimate_chunks(features, StrategyType.SEMANTIC),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.SEMANTIC],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.SEMANTIC],
            pros=["自动识别语义边界", "块大小相对均匀", "无需依赖文档结构"],
            cons=["依赖 Embedding 模型质量", "处理速度较慢"]
        )
    
    def _create_parent_child_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for parent-child chunking."""
        return ChunkingRecommendation(
            strategy=StrategyType.PARENT_CHILD,
            strategy_name=get_strategy_display_name(StrategyType.PARENT_CHILD),
            reason=f"文档较长（{features.total_char_count}字符），父子分块可兼顾检索精度和上下文完整性",
            confidence=0.8,
            estimated_chunks=self._estimate_chunks(features, StrategyType.PARENT_CHILD),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.PARENT_CHILD],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.PARENT_CHILD],
            pros=["小块精确检索", "大块完整上下文", "提升生成质量"],
            cons=["存储量增加", "检索逻辑复杂"]
        )
    
    def _create_character_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for character-based chunking."""
        return ChunkingRecommendation(
            strategy=StrategyType.CHARACTER,
            strategy_name=get_strategy_display_name(StrategyType.CHARACTER),
            reason="文档结构简单，固定字数分块即可满足需求",
            confidence=0.6,
            estimated_chunks=self._estimate_chunks(features, StrategyType.CHARACTER),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.CHARACTER],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.CHARACTER],
            pros=["实现简单", "处理速度快", "块大小可控"],
            cons=["可能截断语义", "不考虑内容结构"]
        )
    
    def _create_paragraph_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for paragraph-based chunking."""
        return ChunkingRecommendation(
            strategy=StrategyType.PARAGRAPH,
            strategy_name=get_strategy_display_name(StrategyType.PARAGRAPH),
            reason="文档内容按段落/行组织，段落分块可保持每条记录的完整性",
            confidence=0.85,
            estimated_chunks=self._estimate_chunks(features, StrategyType.PARAGRAPH),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.PARAGRAPH],
            suggested_params=self.DEFAULT_PARAMS[StrategyType.PARAGRAPH],
            pros=["保持记录完整", "处理速度快", "适合结构化数据"],
            cons=["块大小不均匀", "可能产生很小的块"]
        )
    
    def _estimate_chunks(self, features: DocumentFeatures, strategy: StrategyType) -> int:
        """Estimate number of chunks for a given strategy."""
        if features.total_char_count == 0:
            return 0
        
        avg_chunk_size = self.DEFAULT_CHUNK_SIZES.get(strategy, 500)
        
        # Adjust based on strategy
        if strategy == StrategyType.HEADING:
            # Heading chunks are roughly based on heading count
            return max(features.heading_count, features.total_char_count // avg_chunk_size)
        
        elif strategy == StrategyType.MULTIMODAL:
            # Include table and image chunks
            text_chunks = features.total_char_count // avg_chunk_size
            return text_chunks + features.table_count + features.image_count
        
        elif strategy == StrategyType.PARENT_CHILD:
            # Child chunks (more chunks due to smaller size)
            return features.total_char_count // self.DEFAULT_CHUNK_SIZES[StrategyType.PARENT_CHILD]
        
        else:
            return max(1, features.total_char_count // avg_chunk_size)


# Singleton instance
_service_instance = None


def get_chunking_recommend_service() -> ChunkingRecommendService:
    """Get the chunking recommend service singleton instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ChunkingRecommendService()
    return _service_instance
