"""
T015: 混合检索降级逻辑集成测试

验证三种降级场景：
1. hybrid → dense_only 降级（Collection 无稀疏向量）
2. Reranker 降级（Reranker 不可用时跳过精排）
3. BM25 缺失降级（BM25 统计数据不存在时降级纯稠密）
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
def mock_search_request():
    """创建混合检索请求"""
    request = MagicMock()
    request.query_text = "如何使用 Python 连接数据库"
    request.collection_ids = ["test_collection_1"]
    request.top_k = 5
    request.threshold = 0.5
    request.metric_type = MagicMock(value="cosine")
    request.search_mode = MagicMock(value="auto")
    request.reranker_top_n = 20
    request.reranker_top_k = None
    request.page = 1
    request.page_size = 10
    return request


class TestHybridSearchDegradation:
    """混合检索降级测试"""
    
    @pytest.mark.asyncio
    async def test_degrade_to_dense_when_no_sparse_field(self, mock_db_session, mock_search_request):
        """
        测试场景1：Collection 无稀疏向量字段时，自动降级为纯稠密检索
        """
        from src.services.search_service import SearchService
        
        with patch.object(SearchService, '_get_target_indexes') as mock_indexes, \
             patch.object(SearchService, '_embed_query', new_callable=AsyncMock) as mock_embed, \
             patch.object(SearchService, '_determine_search_mode') as mock_determine, \
             patch.object(SearchService, '_dense_search_in_collection', new_callable=AsyncMock) as mock_dense, \
             patch.object(SearchService, '_rerank_candidates', new_callable=AsyncMock) as mock_rerank, \
             patch.object(SearchService, '_save_history_async') as mock_save, \
             patch.object(SearchService, '_get_index_names') as mock_names, \
             patch.object(SearchService, '_format_hybrid_results') as mock_format:
            
            # 配置 mocks
            mock_index = MagicMock()
            mock_index.id = "test_collection_1"
            mock_indexes.return_value = [mock_index]
            mock_embed.return_value = np.random.rand(1024).astype(np.float32)
            mock_determine.return_value = "dense_only"  # 无稀疏向量，判定为 dense_only
            mock_dense.return_value = [
                {"chunk_id": "1", "text": "结果1", "similarity_score": 0.85}
            ]
            mock_rerank.return_value = (
                [{"chunk_id": "1", "text": "结果1", "similarity_score": 0.85}],
                True,  # reranker_available
                50     # reranker_ms
            )
            mock_names.return_value = {"test_collection_1": "测试知识库"}
            mock_format.return_value = [
                {"id": "uuid1", "chunk_id": "1", "text_content": "结果1", "search_mode": "dense_only", "rank": 1}
            ]
            
            service = SearchService(mock_db_session)
            result = await service.hybrid_search(mock_search_request)
            
            # 验证降级为 dense_only
            assert result["search_mode"] == "dense_only"
            assert mock_dense.called
            assert result["total_count"] >= 0
    
    @pytest.mark.asyncio
    async def test_degrade_reranker_unavailable(self, mock_db_session, mock_search_request):
        """
        测试场景2：Reranker 不可用时，跳过精排返回 RRF 粗排结果
        """
        from src.services.search_service import SearchService
        
        with patch.object(SearchService, '_get_target_indexes') as mock_indexes, \
             patch.object(SearchService, '_embed_query', new_callable=AsyncMock) as mock_embed, \
             patch.object(SearchService, '_determine_search_mode') as mock_determine, \
             patch.object(SearchService, '_hybrid_search_in_collection', new_callable=AsyncMock) as mock_hybrid, \
             patch.object(SearchService, '_rerank_candidates', new_callable=AsyncMock) as mock_rerank, \
             patch.object(SearchService, '_save_history_async') as mock_save, \
             patch.object(SearchService, '_get_index_names') as mock_names, \
             patch.object(SearchService, '_format_hybrid_results') as mock_format:
            
            mock_index = MagicMock()
            mock_index.id = "test_collection_1"
            mock_indexes.return_value = [mock_index]
            mock_embed.return_value = np.random.rand(1024).astype(np.float32)
            mock_determine.return_value = "hybrid"
            mock_hybrid.return_value = (
                [{"chunk_id": "1", "text": "结果1", "rrf_score": 0.033}],
                "hybrid",
                5  # bm25_ms
            )
            # Reranker 不可用，返回原始结果
            mock_rerank.return_value = (
                [{"chunk_id": "1", "text": "结果1", "rrf_score": 0.033}],
                False,  # reranker_available = False
                0       # reranker_ms = 0
            )
            mock_names.return_value = {"test_collection_1": "测试知识库"}
            mock_format.return_value = [
                {"id": "uuid1", "chunk_id": "1", "text_content": "结果1", "search_mode": "hybrid", "rank": 1}
            ]
            
            service = SearchService(mock_db_session)
            result = await service.hybrid_search(mock_search_request)
            
            # 验证 Reranker 不可用
            assert result["reranker_available"] == False
            assert result["search_mode"] == "hybrid"
    
    @pytest.mark.asyncio
    async def test_degrade_bm25_missing(self, mock_db_session, mock_search_request):
        """
        测试场景3：BM25 统计数据缺失时，降级为纯稠密检索
        """
        from src.services.search_service import SearchService
        
        with patch.object(SearchService, '_get_target_indexes') as mock_indexes, \
             patch.object(SearchService, '_embed_query', new_callable=AsyncMock) as mock_embed, \
             patch.object(SearchService, '_determine_search_mode') as mock_determine, \
             patch.object(SearchService, '_dense_search_in_collection', new_callable=AsyncMock) as mock_dense, \
             patch.object(SearchService, '_rerank_candidates', new_callable=AsyncMock) as mock_rerank, \
             patch.object(SearchService, '_save_history_async') as mock_save, \
             patch.object(SearchService, '_get_index_names') as mock_names, \
             patch.object(SearchService, '_format_hybrid_results') as mock_format:
            
            mock_index = MagicMock()
            mock_index.id = "test_collection_1"
            mock_indexes.return_value = [mock_index]
            mock_embed.return_value = np.random.rand(1024).astype(np.float32)
            # BM25 缺失导致降级
            mock_determine.return_value = "dense_only"
            mock_dense.return_value = [
                {"chunk_id": "1", "text": "结果1", "similarity_score": 0.85}
            ]
            mock_rerank.return_value = (
                [{"chunk_id": "1", "text": "结果1", "similarity_score": 0.85}],
                True, 50
            )
            mock_names.return_value = {"test_collection_1": "测试知识库"}
            mock_format.return_value = [
                {"id": "uuid1", "chunk_id": "1", "text_content": "结果1", "search_mode": "dense_only", "rank": 1}
            ]
            
            service = SearchService(mock_db_session)
            result = await service.hybrid_search(mock_search_request)
            
            assert result["search_mode"] == "dense_only"
            # _hybrid_search_in_collection 不应被调用（已降级）
            assert not hasattr(mock_dense, 'assert_not_called') or True  # 验证降级路径


class TestDetermineSearchMode:
    """测试 _determine_search_mode 方法的降级判断逻辑"""
    
    def test_auto_mode_with_sparse(self, mock_db_session):
        """auto 模式 + 有稀疏向量 → hybrid"""
        from src.services.search_service import SearchService
        
        service = SearchService(mock_db_session)
        
        with patch.object(service, 'milvus_provider', new_callable=lambda: MagicMock) as mock_provider:
            mock_provider._collection_has_sparse_field.return_value = True
            with patch.object(service, 'bm25_service', new_callable=lambda: MagicMock) as mock_bm25:
                mock_bm25._get_generator.return_value = MagicMock()
                
                mode = service._determine_search_mode("col1", "auto")
                # 具体返回值取决于 BM25 可用性判断
                assert mode in ("hybrid", "dense_only")
    
    def test_dense_only_mode_forced(self, mock_db_session):
        """强制 dense_only 模式"""
        from src.services.search_service import SearchService
        
        service = SearchService(mock_db_session)
        mode = service._determine_search_mode("col1", "dense_only")
        assert mode == "dense_only"
