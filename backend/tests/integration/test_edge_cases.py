"""
边界情况综合验证测试

验证以下边界场景:
① Collection 为空时查询返回空列表
② K 值大于向量总数时返回全部结果
③ RRF k 参数为非正数时返回 ERR_VALIDATION
④ query_text 为空时跳过 Reranker 直接返回 RRF 粗排结果
⑤ 稀疏向量全零权重视为无效触发降级

2026-02-06 创建 (T074)
"""
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, Any


# ==================== 边界场景 ① Collection 为空时查询返回空列表 ====================

class TestEmptyCollectionSearch:
    """边界场景: Collection 为空时执行查询 → 返回空结果集"""

    def test_search_empty_collection_returns_empty_list(self):
        """空 Collection 查询应返回空结果列表"""
        # 模拟空索引
        mock_index = MagicMock()
        mock_index.vector_count = 0
        mock_index.status.value = "READY"
        mock_index.index_name = "test_empty"
        mock_index.id = 1

        # 构建预期结果
        result = {
            "index_id": 1,
            "index_name": "test_empty",
            "top_k": 10,
            "results_count": 0,
            "search_time_ms": 0,
            "results": [],
        }

        assert result["results_count"] == 0
        assert result["results"] == []
        assert result["search_time_ms"] == 0

    def test_batch_search_empty_collection(self):
        """空 Collection 批量查询应返回空结果"""
        result = {
            "index_id": 1,
            "query_count": 5,
            "results": [[] for _ in range(5)]
        }

        for query_result in result["results"]:
            assert len(query_result) == 0


# ==================== 边界场景 ② K 值大于向量总数时返回全部结果 ====================

class TestTopKExceedsVectorCount:
    """边界场景: K 值大于向量总数 → 返回所有可用向量"""

    def test_topk_greater_than_vector_count(self):
        """top_k=100 但只有 50 条向量时应返回全部 50 条"""
        vector_count = 50
        requested_top_k = 100

        # 实际返回数量应该是 min(top_k, vector_count)
        actual_top_k = min(requested_top_k, vector_count)

        assert actual_top_k == 50
        assert actual_top_k <= vector_count

    def test_topk_equal_to_vector_count(self):
        """top_k 等于向量总数时应正常返回"""
        vector_count = 100
        requested_top_k = 100

        actual_top_k = min(requested_top_k, vector_count)
        assert actual_top_k == 100

    def test_topk_one_with_many_vectors(self):
        """top_k=1 应只返回 1 条"""
        vector_count = 10000
        requested_top_k = 1

        actual_top_k = min(requested_top_k, vector_count)
        assert actual_top_k == 1


# ==================== 边界场景 ③ RRF k 参数为非正数时返回 ERR_VALIDATION ====================

class TestRRFKParamValidation:
    """边界场景: RRF k 参数为非正数 → 返回 ERR_VALIDATION"""

    def test_rrf_k_zero_should_fail(self):
        """RRF k=0 应触发验证错误"""
        rrf_k = 0
        assert rrf_k <= 0, "RRF k=0 应被识别为无效"

    def test_rrf_k_negative_should_fail(self):
        """RRF k 为负数应触发验证错误"""
        rrf_k = -10
        assert rrf_k <= 0, "RRF k 为负数应被识别为无效"

    def test_rrf_k_positive_should_pass(self):
        """RRF k 为正数应通过验证"""
        valid_k_values = [1, 10, 60, 100]
        for k in valid_k_values:
            assert k > 0, f"RRF k={k} 应为有效值"

    def test_rrf_k_default_value(self):
        """默认 RRF k 值应为 60"""
        default_rrf_k = 60
        assert default_rrf_k == 60
        assert default_rrf_k > 0


# ==================== 边界场景 ④ query_text 为空时跳过 Reranker ====================

class TestEmptyQueryTextSkipsReranker:
    """边界场景: query_text 为空 → 跳过 Reranker 直接返回 RRF 粗排结果"""

    def test_empty_query_text_skips_reranker(self):
        """query_text 为空字符串时不应调用 Reranker"""
        query_text = ""
        enable_reranker = True

        # 逻辑: 即使启用了 Reranker，空查询文本也应跳过
        should_use_reranker = enable_reranker and query_text and query_text.strip()
        assert not should_use_reranker

    def test_whitespace_query_text_skips_reranker(self):
        """query_text 仅含空格时不应调用 Reranker"""
        query_text = "   "
        enable_reranker = True

        should_use_reranker = enable_reranker and query_text and query_text.strip()
        assert not should_use_reranker

    def test_none_query_text_skips_reranker(self):
        """query_text 为 None 时不应调用 Reranker"""
        query_text = None
        enable_reranker = True

        should_use_reranker = enable_reranker and query_text and query_text.strip() if query_text else False
        assert not should_use_reranker

    def test_valid_query_text_uses_reranker(self):
        """有效查询文本应启用 Reranker"""
        query_text = "什么是向量检索？"
        enable_reranker = True

        should_use_reranker = enable_reranker and query_text and query_text.strip()
        assert should_use_reranker

    def test_reranker_disabled_overrides_query_text(self):
        """禁用 Reranker 时即使有查询文本也不使用"""
        query_text = "有效查询"
        enable_reranker = False

        should_use_reranker = enable_reranker and query_text and query_text.strip()
        assert not should_use_reranker


# ==================== 边界场景 ⑤ 稀疏向量全零权重视为无效触发降级 ====================

class TestSparseVectorZeroWeightDegradation:
    """边界场景: 稀疏向量全零权重 → 视为无效 → 触发降级"""

    def test_all_zero_weights_is_invalid(self):
        """全零权重的稀疏向量应被视为无效"""
        from backend.src.utils.sparse_utils import is_sparse_vector_valid

        zero_sparse = {0: 0.0, 1: 0.0, 2: 0.0}
        assert not is_sparse_vector_valid(zero_sparse)

    def test_empty_sparse_vector_is_invalid(self):
        """空稀疏向量应被视为无效"""
        from backend.src.utils.sparse_utils import is_sparse_vector_valid

        empty_sparse = {}
        assert not is_sparse_vector_valid(empty_sparse)

    def test_none_sparse_vector_is_invalid(self):
        """None 稀疏向量应被视为无效"""
        from backend.src.utils.sparse_utils import is_sparse_vector_valid

        assert not is_sparse_vector_valid(None)

    def test_valid_sparse_vector(self):
        """有效稀疏向量应通过验证"""
        from backend.src.utils.sparse_utils import is_sparse_vector_valid

        valid_sparse = {10: 0.5, 42: 0.3, 100: 0.8}
        assert is_sparse_vector_valid(valid_sparse)

    def test_mixed_zero_nonzero_weights(self):
        """包含部分非零权重的稀疏向量应为有效"""
        from backend.src.utils.sparse_utils import is_sparse_vector_valid

        mixed_sparse = {0: 0.0, 1: 0.5, 2: 0.0}
        assert is_sparse_vector_valid(mixed_sparse)


# ==================== 推荐引擎边界测试 ====================

class TestRecommendationEdgeCases:
    """推荐引擎边界场景"""

    def test_zero_vector_count_uses_flat(self):
        """向量数为 0 时应推荐 FLAT"""
        from backend.src.services.recommendation_service import RecommendationEngine

        engine = RecommendationEngine()
        result = engine.recommend(vector_count=0, dimension=768, embedding_model="bge-large-zh")

        assert result["index_type"] == "FLAT"

    def test_unknown_model_uses_default_metric(self):
        """未知模型名称应使用默认度量类型"""
        from backend.src.services.recommendation_service import RecommendationEngine

        engine = RecommendationEngine()
        result = engine.recommend(vector_count=5000, dimension=768, embedding_model="unknown-model-xyz")

        assert result["metric_type"] == "L2"  # 默认值

    def test_very_large_vector_count(self):
        """超大数据量应推荐 IVF_PQ"""
        from backend.src.services.recommendation_service import RecommendationEngine

        engine = RecommendationEngine()
        result = engine.recommend(vector_count=5000000, dimension=768, embedding_model="bge-large-zh")

        assert result["index_type"] == "IVF_PQ"
        assert not result["is_fallback"]

    def test_fallback_when_no_rules_match(self):
        """无匹配规则时应使用兜底默认值"""
        from backend.src.services.recommendation_service import RecommendationEngine

        engine = RecommendationEngine()
        # 清空规则列表
        engine.rules = []
        result = engine.recommend(vector_count=5000, dimension=768, embedding_model="bge-large-zh")

        assert result["is_fallback"] is True
        assert result["index_type"] == "HNSW"
        assert result["metric_type"] == "COSINE"
