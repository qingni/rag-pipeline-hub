"""
T016: Reranker 集成测试

验证 RerankerService 与 SearchService 的集成：
1. 候选集格式适配
2. 降级返回（Reranker 不可用时）
3. 正常精排流程
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np


@pytest.fixture
def mock_db_session():
    """创建 mock 数据库会话"""
    session = MagicMock()
    session.query.return_value.filter.return_value.count.return_value = 0
    return session


class TestRerankerIntegration:
    """Reranker 集成测试"""
    
    @pytest.mark.asyncio
    async def test_rerank_candidates_success(self, mock_db_session):
        """测试正常精排流程"""
        from src.services.search_service import SearchService
        
        service = SearchService(mock_db_session)
        
        candidates = [
            {
                "chunk_id": "1",
                "text": "Python 连接数据库的方法",
                "similarity_score": 0.85,
                "metadata": {"source_text": "Python 连接数据库的方法"}
            },
            {
                "chunk_id": "2", 
                "text": "数据库连接池配置",
                "similarity_score": 0.75,
                "metadata": {"source_text": "数据库连接池配置"}
            }
        ]
        
        with patch.object(service, 'reranker_service', new_callable=lambda: MagicMock) as mock_reranker:
            mock_reranker.available = True
            mock_reranker.rerank.return_value = [
                {
                    "chunk_id": "1",
                    "text": "Python 连接数据库的方法",
                    "reranker_score": 0.95,
                    "similarity_score": 0.85,
                    "metadata": {"source_text": "Python 连接数据库的方法"}
                },
                {
                    "chunk_id": "2",
                    "text": "数据库连接池配置",
                    "reranker_score": 0.72,
                    "similarity_score": 0.75,
                    "metadata": {"source_text": "数据库连接池配置"}
                }
            ]
            
            ranked, available, reranker_ms = await service._rerank_candidates(
                query_text="如何使用 Python 连接数据库",
                candidates=candidates,
                top_k=5,
                reranker_top_n=20
            )
            
            assert available == True
            assert len(ranked) == 2
    
    @pytest.mark.asyncio
    async def test_rerank_candidates_unavailable(self, mock_db_session):
        """测试 Reranker 不可用时的降级"""
        from src.services.search_service import SearchService
        
        service = SearchService(mock_db_session)
        
        candidates = [
            {"chunk_id": "1", "text": "测试", "similarity_score": 0.85},
            {"chunk_id": "2", "text": "测试2", "similarity_score": 0.75}
        ]
        
        with patch.object(service, 'reranker_service', new_callable=lambda: MagicMock) as mock_reranker:
            mock_reranker.available = False
            
            ranked, available, reranker_ms = await service._rerank_candidates(
                query_text="测试查询",
                candidates=candidates,
                top_k=5,
                reranker_top_n=20
            )
            
            # Reranker 不可用时应返回原始候选集
            assert available == False
            assert reranker_ms == 0
            assert len(ranked) <= 5
    
    @pytest.mark.asyncio
    async def test_rerank_empty_candidates(self, mock_db_session):
        """测试空候选集的处理"""
        from src.services.search_service import SearchService
        
        service = SearchService(mock_db_session)
        
        with patch.object(service, 'reranker_service', new_callable=lambda: MagicMock) as mock_reranker:
            mock_reranker.available = True
            
            ranked, available, reranker_ms = await service._rerank_candidates(
                query_text="测试查询",
                candidates=[],
                top_k=5,
                reranker_top_n=20
            )
            
            assert len(ranked) == 0


class TestRerankerHealthEndpoint:
    """Reranker 健康检查端点测试"""
    
    def test_reranker_health_response_format(self):
        """验证 RerankerHealthResponse 格式"""
        from src.schemas.search import RerankerHealthData
        
        health_data = RerankerHealthData(
            available=True,
            model_name="qwen3-reranker-4b",
            use_fp16=True,
            flag_embedding_installed=True,
            model_loaded=True
        )
        
        assert health_data.available == True
        assert health_data.model_name == "qwen3-reranker-4b"
    
    def test_reranker_health_unavailable(self):
        """验证 Reranker 不可用时的响应格式"""
        from src.schemas.search import RerankerHealthData
        
        health_data = RerankerHealthData(
            available=False,
            model_name="qwen3-reranker-4b",
            use_fp16=True,
            flag_embedding_installed=False,
            model_loaded=False
        )
        
        assert health_data.available == False
        assert health_data.flag_embedding_installed == False
