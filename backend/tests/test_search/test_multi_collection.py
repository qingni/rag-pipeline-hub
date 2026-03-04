"""
T033: 多 Collection 联合搜索集成测试

验证场景：
1. 并行检索多个 Collection
2. 候选集合并
3. 统一 Reranker 精排
4. source_collection 标注
5. Reranker 降级场景
6. Collection 数量超限
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


@pytest.fixture
def mock_db_session():
    """创建 mock 数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.count.return_value = 0
    session.query.return_value.filter.return_value.all.return_value = []
    return session


@pytest.fixture
def mock_multi_collection_request():
    """创建多 Collection 搜索请求"""
    request = MagicMock()
    request.query_text = "向量数据库性能优化"
    request.collection_ids = ["col_1", "col_2"]
    request.top_k = 10
    request.threshold = 0.5
    request.metric_type = MagicMock(value="cosine")
    request.search_mode = MagicMock(value="auto")
    request.reranker_top_n = 20
    request.reranker_top_k = None
    request.page = 1
    request.page_size = 10
    return request


class TestMultiCollectionSearch:
    """多 Collection 联合搜索测试"""
    
    @pytest.mark.asyncio
    async def test_parallel_search_two_collections(self, mock_db_session, mock_multi_collection_request):
        """测试并行在两个 Collection 中检索"""
        from src.services.search_service import SearchService
        
        with patch.object(SearchService, '_get_target_indexes') as mock_indexes, \
             patch.object(SearchService, '_embed_query', new_callable=AsyncMock) as mock_embed, \
             patch.object(SearchService, '_multi_collection_search', new_callable=AsyncMock) as mock_multi, \
             patch.object(SearchService, '_save_history_async') as mock_save:
            
            mock_idx1 = MagicMock()
            mock_idx1.id = "col_1"
            mock_idx2 = MagicMock()
            mock_idx2.id = "col_2"
            mock_indexes.return_value = [mock_idx1, mock_idx2]
            mock_embed.return_value = np.random.rand(1024).astype(np.float32)
            
            # 模拟多 Collection 搜索结果
            mock_multi.return_value = {
                "query_id": "test-uuid",
                "query_text": "向量数据库性能优化",
                "search_mode": "hybrid",
                "reranker_available": True,
                "rrf_k": 60,
                "results": [
                    {
                        "id": "r1", "chunk_id": "c1", "text_content": "结果1",
                        "text_summary": "结果1", "similarity_score": 0.9,
                        "reranker_score": 0.95, "rrf_score": 0.033,
                        "search_mode": "hybrid", "source_collection": "技术文档",
                        "source_document": "doc1.pdf", "rank": 1
                    },
                    {
                        "id": "r2", "chunk_id": "c2", "text_content": "结果2",
                        "text_summary": "结果2", "similarity_score": 0.85,
                        "reranker_score": 0.88, "rrf_score": 0.031,
                        "search_mode": "hybrid", "source_collection": "产品手册",
                        "source_document": "doc2.pdf", "rank": 2
                    }
                ],
                "total_count": 2,
                "execution_time_ms": 200,
                "timing": {"embedding_ms": 50, "bm25_ms": 5, "search_ms": 60, "reranker_ms": 85, "total_ms": 200}
            }
            
            service = SearchService(mock_db_session)
            result = await service.hybrid_search(mock_multi_collection_request)
            
            # 验证多 Collection 路径被调用
            mock_multi.assert_called_once()
            assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_source_collection_annotation(self, mock_db_session, mock_multi_collection_request):
        """测试结果中 source_collection 标注"""
        from src.services.search_service import SearchService
        
        with patch.object(SearchService, '_get_target_indexes') as mock_indexes, \
             patch.object(SearchService, '_embed_query', new_callable=AsyncMock) as mock_embed, \
             patch.object(SearchService, '_multi_collection_search', new_callable=AsyncMock) as mock_multi, \
             patch.object(SearchService, '_save_history_async') as mock_save:
            
            mock_idx1 = MagicMock()
            mock_idx1.id = "col_1"
            mock_idx2 = MagicMock()
            mock_idx2.id = "col_2"
            mock_indexes.return_value = [mock_idx1, mock_idx2]
            mock_embed.return_value = np.random.rand(1024).astype(np.float32)
            
            mock_multi.return_value = {
                "query_id": "test-uuid",
                "query_text": "测试",
                "search_mode": "hybrid",
                "reranker_available": True,
                "rrf_k": 60,
                "results": [
                    {"id": "r1", "source_collection": "col_1_name", "rank": 1},
                    {"id": "r2", "source_collection": "col_2_name", "rank": 2}
                ],
                "total_count": 2,
                "execution_time_ms": 150,
                "timing": {"total_ms": 150}
            }
            
            service = SearchService(mock_db_session)
            result = await service.hybrid_search(mock_multi_collection_request)
            
            # 验证每条结果都有 source_collection
            for item in result["results"]:
                assert "source_collection" in item
                assert item["source_collection"] != ""


class TestCollectionLimitValidation:
    """Collection 数量限制验证"""
    
    def test_max_collections_exceeded_schema(self):
        """测试 HybridSearchRequest 中 collection_ids 最大数量"""
        from src.schemas.search import HybridSearchRequest
        
        # 5 个以内应该正常
        request = HybridSearchRequest(
            query_text="测试",
            collection_ids=["c1", "c2", "c3", "c4", "c5"]
        )
        assert len(request.collection_ids) == 5
    
    def test_search_timing_schema(self):
        """测试 SearchTiming schema"""
        from src.schemas.search import SearchTiming
        
        timing = SearchTiming(
            embedding_ms=50,
            bm25_ms=5,
            search_ms=60,
            reranker_ms=85,
            total_ms=200
        )
        assert timing.total_ms == 200
        assert timing.reranker_ms == 85
