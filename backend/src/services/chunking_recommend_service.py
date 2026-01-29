"""Chunking recommendation service for intelligent strategy selection.

使用智能参数配置模块，根据文档类型、长度、Embedding 模型等特征
动态推荐最优的分块参数。
"""
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

# 导入智能参数配置模块
from ..config.smart_params import (
    FORMAT_BASE_PARAMS,
    EMBEDDING_MODEL_PARAMS,
    get_base_text_params,
    get_adaptive_text_params,
    get_semantic_params,
    get_hybrid_params,
    get_parent_child_params,
    get_heading_params,
    get_paragraph_params,
    get_character_params,
    get_smart_params,
    get_document_length_category,
    DocumentLength
)


class ChunkingRecommendService:
    """Service for recommending optimal chunking strategies.
    
    Uses a rule-based engine to analyze document features and
    recommend the most suitable chunking strategies.
    
    现在使用智能参数配置模块 (smart_params.py) 提供：
    - 基于文档格式的基础参数
    - 基于文档长度的自适应调整
    - 基于 Embedding 模型的语义分块参数
    - 各策略的专用参数配置
    """
    
    # Default chunk size estimates for each strategy
    DEFAULT_CHUNK_SIZES = {
        StrategyType.CHARACTER: 500,
        StrategyType.PARAGRAPH: 800,
        StrategyType.HEADING: 1500,
        StrategyType.SEMANTIC: 1000,
        StrategyType.PARENT_CHILD: 400,  # Child chunk size
        StrategyType.HYBRID: 800,
    }
    
    def __init__(self):
        self.analyzer = get_document_analyzer()
    
    def get_format_params(self, document_format: str) -> Dict[str, Any]:
        """
        根据文档格式获取推荐的分块参数（使用智能参数模块）。
        
        Args:
            document_format: 文档格式（如 'pdf', 'csv', 'docx'）
            
        Returns:
            包含 chunk_size 和 overlap 的字典
        """
        return get_base_text_params(document_format)
    
    def get_adaptive_params(self, document_format: str, char_count: int) -> Dict[str, Any]:
        """
        根据文档格式和长度自适应调整参数（使用智能参数模块）。
        
        短文档用小块，长文档用大块。
        
        Args:
            document_format: 文档格式
            char_count: 文档字符数
            
        Returns:
            自适应调整后的分块参数
        """
        return get_adaptive_text_params(document_format, char_count)
    
    def get_format_params_with_description(self, document_format: str) -> Dict[str, Any]:
        """
        获取格式参数及其描述说明。
        
        Args:
            document_format: 文档格式
            
        Returns:
            包含 chunk_size, overlap 和 description 的完整配置
        """
        fmt = document_format.lower() if document_format else "default"
        config = FORMAT_BASE_PARAMS.get(fmt, FORMAT_BASE_PARAMS["default"])
        return {
            "chunk_size": config["chunk_size"],
            "overlap": config["overlap"],
            "description": config.get("description", "")
        }
    
    def get_smart_strategy_params(
        self, 
        strategy_type: str,
        features: DocumentFeatures,
        embedding_model: str = "bge-m3"
    ) -> Dict[str, Any]:
        """
        获取策略的智能参数配置。
        
        根据策略类型、文档特征和 Embedding 模型，返回最优参数。
        
        Args:
            strategy_type: 策略类型
            features: 文档特征
            embedding_model: Embedding 模型名称
            
        Returns:
            策略对应的智能参数配置
        """
        return get_smart_params(
            strategy_type=strategy_type,
            doc_format=features.document_format or "default",
            char_count=features.total_char_count,
            embedding_model=embedding_model,
            code_block_ratio=features.code_block_ratio,
            table_count=features.table_count,
            image_count=features.image_count,
            heading_count=features.heading_count,
            # 新增：传递正文策略推荐相关的特征
            has_table_layout=features.has_table_layout,
            is_flattened_tabular=features.is_flattened_tabular,
            is_log_like=features.is_log_like,
            is_slide_like=features.is_slide_like,
            has_clear_structure=features.has_clear_structure
        )
    
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
        
        # 检测多模态内容（表格、图片等需要特殊处理的内容）
        has_multimodal = features.table_count >= 1 or features.image_count >= 1
        has_rich_multimodal = features.table_count >= 3 or features.image_count >= 3
        
        # Rule 1: Multimodal content -> Hybrid chunking
        # 只要包含图片或表格就推荐，因为图片/表格是独立的信息单元
        if has_multimodal:
            rec = self._create_hybrid_multimodal_recommendation(features)
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
        """Create recommendation for heading-based chunking with smart params."""
        heading_summary = features.get_heading_summary()
        
        # 使用智能参数
        smart_params = get_heading_params(
            features.document_format or "default",
            features.heading_count
        )
        
        return ChunkingRecommendation(
            strategy=StrategyType.HEADING,
            strategy_name=get_strategy_display_name(StrategyType.HEADING),
            reason=f"检测到清晰的标题层级结构（{heading_summary}），{smart_params.get('description', '')}",
            confidence=0.9 if features.heading_count > 10 else 0.8,
            estimated_chunks=self._estimate_chunks(features, StrategyType.HEADING),
            estimated_avg_chunk_size=self.DEFAULT_CHUNK_SIZES[StrategyType.HEADING],
            suggested_params={
                "min_heading_level": smart_params["min_heading_level"],
                "max_heading_level": smart_params["max_heading_level"]
            },
            pros=["保持章节完整性", "语义边界清晰", "适合检索问答"],
            cons=["块大小不均匀", "依赖文档结构质量"]
        )
    
    def _create_hybrid_multimodal_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """
        Create recommendation for hybrid chunking with multimodal content.
        """
        multimodal_summary = features.get_multimodal_summary()
        fmt = features.document_format or "default"
        
        # 使用智能参数（包含正文策略推荐）
        smart_params = get_hybrid_params(
            doc_format=fmt,
            char_count=features.total_char_count,
            code_block_ratio=features.code_block_ratio,
            embedding_model="bge-m3",
            has_tables=features.table_count > 0,
            has_images=features.image_count > 0,
            has_code=features.code_block_ratio > 0,
            # 新增：传递正文策略推荐相关的特征
            has_table_layout=features.has_table_layout,
            is_flattened_tabular=features.is_flattened_tabular,
            is_log_like=features.is_log_like,
            is_slide_like=features.is_slide_like,
            has_clear_structure=features.has_clear_structure,
            heading_count=features.heading_count
        )
        
        # 根据多模态内容数量生成不同的推荐理由
        if features.image_count >= 3 or features.table_count >= 3:
            reason = f"文档包含丰富的多内容类型（{multimodal_summary}），图片/表格作为独立信息单元需要独立分块检索"
        elif features.image_count >= 1 and features.table_count >= 1:
            reason = f"文档同时包含图片和表格（{multimodal_summary}），混合分块可分别独立检索"
        elif features.image_count >= 1:
            reason = f"文档包含图片内容（{multimodal_summary}），图片是完整的视觉信息单元，应独立分块"
        else:
            reason = f"文档包含表格内容（{multimodal_summary}），表格是结构化数据单元，应独立分块"
        
        # 添加参数调整说明
        if smart_params.get("length_adjustment"):
            reason += f"（{smart_params['length_adjustment']}）"
        
        # 添加正文策略推荐说明
        text_strategy_reason = smart_params.get("text_strategy_reason", "")
        if text_strategy_reason:
            reason += f"。正文策略：{text_strategy_reason}"
        
        # 根据推荐的正文策略调整优势说明
        text_strategy = smart_params.get("text_strategy", "semantic")
        pros = ["图片/表格独立检索", "支持多内容类型提取", "内容类型区分清晰"]
        
        if text_strategy == "paragraph":
            pros.append(f"正文按段落分块保持记录完整")
        elif text_strategy == "heading":
            pros.append(f"正文按标题分块保持章节完整")
        else:
            pros.append(f"正文语义分块识别自然边界")
        
        pros.append(f"参数针对 {fmt.upper()} 格式优化")
        
        return ChunkingRecommendation(
            strategy=StrategyType.HYBRID,
            strategy_name=get_strategy_display_name(StrategyType.HYBRID),
            reason=reason,
            confidence=0.85,
            estimated_chunks=self._estimate_chunks(features, StrategyType.HYBRID),
            estimated_avg_chunk_size=smart_params["text_chunk_size"],
            suggested_params=smart_params,
            pros=pros,
            cons=["配置项较多", "处理复杂度较高"]
        )
    
    def _create_hybrid_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for hybrid chunking with smart params."""
        fmt = features.document_format or "default"
        
        # 使用智能参数（包含正文策略推荐）
        smart_params = get_hybrid_params(
            doc_format=fmt,
            char_count=features.total_char_count,
            code_block_ratio=features.code_block_ratio,
            embedding_model="bge-m3",
            # 新增：传递正文策略推荐相关的特征
            has_table_layout=features.has_table_layout,
            is_flattened_tabular=features.is_flattened_tabular,
            is_log_like=features.is_log_like,
            is_slide_like=features.is_slide_like,
            has_clear_structure=features.has_clear_structure,
            heading_count=features.heading_count
        )
        
        reason = f"检测到技术文档特征（代码占比 {features.code_block_ratio:.1%}），建议混合策略"
        if smart_params.get("length_adjustment"):
            reason += f"（{smart_params['length_adjustment']}）"
        
        # 添加正文策略推荐说明
        text_strategy_reason = smart_params.get("text_strategy_reason", "")
        if text_strategy_reason:
            reason += f"。正文策略：{text_strategy_reason}"
        
        return ChunkingRecommendation(
            strategy=StrategyType.HYBRID,
            strategy_name=get_strategy_display_name(StrategyType.HYBRID),
            reason=reason,
            confidence=0.82,
            estimated_chunks=self._estimate_chunks(features, StrategyType.HYBRID),
            estimated_avg_chunk_size=smart_params["text_chunk_size"],
            suggested_params=smart_params,
            pros=["各类内容针对性处理", "代码保持完整性", "文本语义分块", f"代码块 {smart_params['code_chunk_lines']} 行/块"],
            cons=["配置复杂度高", "需要理解各策略参数"]
        )
    
    def _create_semantic_recommendation(
        self, 
        features: DocumentFeatures,
        baseline: bool = False,
        embedding_model: str = "bge-m3"
    ) -> ChunkingRecommendation:
        """Create recommendation for semantic chunking with smart params."""
        # 使用智能参数，结合 Embedding 模型
        smart_params = get_semantic_params(
            embedding_model=embedding_model,
            doc_format=features.document_format,
            char_count=features.total_char_count
        )
        
        if baseline:
            reason = "语义分块是通用策略，适合大多数文档类型"
            confidence = 0.7
        else:
            reason = f"检测到连续叙事文本，无明显标题结构，语义分块可识别自然边界"
            if smart_params.get("length_adjustment"):
                reason += f"（{smart_params['length_adjustment']}）"
            confidence = 0.85
        
        # 添加模型说明
        model_desc = smart_params.get("model_description", "")
        if model_desc:
            reason += f"。推荐模型：{model_desc}"
        
        return ChunkingRecommendation(
            strategy=StrategyType.SEMANTIC,
            strategy_name=get_strategy_display_name(StrategyType.SEMANTIC),
            reason=reason,
            confidence=confidence,
            estimated_chunks=self._estimate_chunks(features, StrategyType.SEMANTIC),
            estimated_avg_chunk_size=(smart_params["min_chunk_size"] + smart_params["max_chunk_size"]) // 2,
            suggested_params=smart_params,
            pros=["自动识别语义边界", "块大小相对均匀", "无需依赖文档结构", f"阈值 {smart_params['similarity_threshold']} 针对 {embedding_model} 优化"],
            cons=["依赖 Embedding 模型质量", "处理速度较慢"]
        )
    
    def _create_parent_child_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for parent-child chunking with smart params."""
        # 使用智能参数
        smart_params = get_parent_child_params(
            char_count=features.total_char_count,
            doc_format=features.document_format
        )
        
        reason = f"文档较长（{features.total_char_count}字符），父子分块可兼顾检索精度和上下文完整性"
        if smart_params.get("adjustment_reason"):
            reason += f"（{smart_params['adjustment_reason']}）"
        
        return ChunkingRecommendation(
            strategy=StrategyType.PARENT_CHILD,
            strategy_name=get_strategy_display_name(StrategyType.PARENT_CHILD),
            reason=reason,
            confidence=0.8,
            estimated_chunks=self._estimate_chunks(features, StrategyType.PARENT_CHILD),
            estimated_avg_chunk_size=smart_params["child_chunk_size"],
            suggested_params=smart_params,
            pros=["小块精确检索", "大块完整上下文", "提升生成质量", f"父块 {smart_params['parent_chunk_size']} / 子块 {smart_params['child_chunk_size']}"],
            cons=["存储量增加", "检索逻辑复杂"]
        )
    
    def _create_character_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for character-based chunking with smart params."""
        fmt = features.document_format or "default"
        
        # 使用智能参数
        smart_params = get_character_params(fmt, features.total_char_count)
        
        # 构建推荐理由
        if fmt != "default":
            reason = f"文档格式为 {fmt.upper()}，推荐 chunk_size={smart_params['chunk_size']}, overlap={smart_params['overlap']}"
            if smart_params.get("base_description"):
                reason += f"（{smart_params['base_description']}）"
        else:
            reason = "文档结构简单，固定字数分块即可满足需求"
        
        if smart_params.get("adjustment_reason"):
            reason += f"。{smart_params['adjustment_reason']}"
        
        return ChunkingRecommendation(
            strategy=StrategyType.CHARACTER,
            strategy_name=get_strategy_display_name(StrategyType.CHARACTER),
            reason=reason,
            confidence=0.6,
            estimated_chunks=max(1, features.total_char_count // smart_params["chunk_size"]) if features.total_char_count > 0 else 0,
            estimated_avg_chunk_size=smart_params["chunk_size"],
            suggested_params={
                "chunk_size": smart_params["chunk_size"],
                "overlap": smart_params["overlap"]
            },
            pros=["实现简单", "处理速度快", "块大小可控", f"针对 {fmt.upper()} 格式优化"],
            cons=["可能截断语义", "不考虑内容结构"]
        )
    
    def _create_paragraph_recommendation(self, features: DocumentFeatures) -> ChunkingRecommendation:
        """Create recommendation for paragraph-based chunking with smart params."""
        # 使用智能参数
        smart_params = get_paragraph_params(features.total_char_count)
        
        reason = "文档内容按段落/行组织，段落分块可保持每条记录的完整性"
        if smart_params.get("adjustment_reason"):
            reason += f"（{smart_params['adjustment_reason']}）"
        
        return ChunkingRecommendation(
            strategy=StrategyType.PARAGRAPH,
            strategy_name=get_strategy_display_name(StrategyType.PARAGRAPH),
            reason=reason,
            confidence=0.85,
            estimated_chunks=self._estimate_chunks(features, StrategyType.PARAGRAPH),
            estimated_avg_chunk_size=(smart_params["min_chunk_size"] + smart_params["max_chunk_size"]) // 2,
            suggested_params=smart_params,
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
        
        elif strategy == StrategyType.HYBRID:
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
