"""
智能推荐引擎服务

根据向量特征（维度、数据量、Embedding 模型类型）自动推荐索引算法和度量类型。
采用分层规则匹配策略，支持 JSON 配置热更新和兜底默认值。

2026-02-06 创建 (T018, T019)
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..models.vector_index import RecommendationRule, RecommendationLog

logger = logging.getLogger("recommendation_service")


# 度量类型推荐规则（按模型系列前缀匹配）
METRIC_TYPE_RULES = {
    "bge": "COSINE",
    "qwen": "COSINE",  # Qwen 系列（qwen3-embedding-8b, qwen3-vl-embedding-8b 等）
    "openai": "COSINE",
    "cohere": "COSINE",
    "text-embedding": "COSINE",  # OpenAI text-embedding-xxx
    "ada": "COSINE",  # OpenAI ada
    "default": "L2",
}

# 兜底默认值
FALLBACK_RECOMMENDATION = {
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "reason": "未精确匹配推荐规则，已使用通用默认值",
}


class RecommendationRuleConfig:
    """推荐规则配置（来自 JSON 文件）"""

    def __init__(
        self,
        rule_id: str,
        priority: int,
        min_vector_count: Optional[int] = None,
        max_vector_count: Optional[int] = None,
        min_dimension: Optional[int] = None,
        max_dimension: Optional[int] = None,
        embedding_models: Optional[List[str]] = None,
        recommended_index_type: str = "HNSW",
        recommended_metric_type: Optional[str] = None,
        reason_template: str = "",
    ):
        self.rule_id = rule_id
        self.priority = priority
        self.min_vector_count = min_vector_count
        self.max_vector_count = max_vector_count
        self.min_dimension = min_dimension
        self.max_dimension = max_dimension
        self.embedding_models = embedding_models
        self.recommended_index_type = recommended_index_type
        self.recommended_metric_type = recommended_metric_type
        self.reason_template = reason_template


class RecommendationEngine:
    """
    智能推荐引擎

    基于分层规则匹配策略，自动推荐索引算法和度量类型。
    规则优先级：数据量 → 向量维度 → Embedding 模型类型。
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化推荐引擎

        Args:
            config_path: 推荐规则 JSON 配置文件路径（可选）
        """
        self.rules: List[RecommendationRuleConfig] = []
        self.metric_type_rules: Dict[str, str] = METRIC_TYPE_RULES.copy()
        self.fallback = FALLBACK_RECOMMENDATION.copy()

        if config_path:
            self._load_rules_from_file(config_path)
        else:
            # 尝试加载默认配置文件
            default_path = Path(__file__).parent.parent / "config" / "recommendation_rules.json"
            if default_path.exists():
                self._load_rules_from_file(str(default_path))
            else:
                self._load_default_rules()

        logger.info(f"RecommendationEngine 初始化完成，加载 {len(self.rules)} 条规则")

    def _load_rules_from_file(self, config_path: str) -> None:
        """从 JSON 文件加载推荐规则"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 加载规则
            for rule_data in config.get("rules", []):
                self.rules.append(RecommendationRuleConfig(**rule_data))

            # 加载度量类型规则
            if "metric_type_rules" in config:
                self.metric_type_rules.update(config["metric_type_rules"])

            # 加载兜底默认值
            if "fallback" in config:
                self.fallback.update(config["fallback"])

            # 按优先级排序
            self.rules.sort(key=lambda r: r.priority)

            logger.info(f"从 {config_path} 加载 {len(self.rules)} 条推荐规则")

        except Exception as e:
            logger.error(f"加载推荐规则失败: {e}，使用默认规则")
            self._load_default_rules()

    def _load_default_rules(self) -> None:
        """加载默认推荐规则（与 recommendation_rules.json 保持同步）"""
        self.rules = [
            RecommendationRuleConfig(
                rule_id="rule_small_data",
                priority=1,
                min_vector_count=0,
                max_vector_count=9999,
                recommended_index_type="FLAT",
                reason_template="数据量 {count} 条 < 1万，FLAT 暴力搜索保证 100% 精确召回",
            ),
            RecommendationRuleConfig(
                rule_id="rule_medium_data",
                priority=2,
                min_vector_count=10000,
                max_vector_count=499999,
                recommended_index_type="HNSW",
                reason_template="数据量 {count} 条（1万~50万），HNSW 图索引兼顾高召回率与低延迟，业界首选",
            ),
            RecommendationRuleConfig(
                rule_id="rule_large_data",
                priority=3,
                min_vector_count=500000,
                max_vector_count=4999999,
                recommended_index_type="IVF_SQ8",
                reason_template="数据量 {count} 条（50万~500万），IVF_SQ8 标量量化在精度损失极小的情况下节省约 75% 内存",
            ),
            RecommendationRuleConfig(
                rule_id="rule_massive_data",
                priority=4,
                min_vector_count=5000000,
                recommended_index_type="IVF_PQ",
                reason_template="数据量 {count} 条 ≥ 500万，IVF_PQ 乘积量化大幅压缩内存占用",
            ),
        ]

    def recommend(
        self,
        vector_count: int,
        dimension: int,
        embedding_model: str = "",
    ) -> Dict[str, Any]:
        """
        根据向量特征推荐索引算法和度量类型

        Args:
            vector_count: 向量数据量
            dimension: 向量维度
            embedding_model: Embedding 模型名称

        Returns:
            推荐结果字典:
            {
                "index_type": str,
                "metric_type": str,
                "reason": str,
                "is_fallback": bool,
                "vector_count": int,
                "dimension": int,
                "embedding_model": str,
            }
        """
        # 1. 匹配索引算法规则
        matched_rule = None
        for rule in self.rules:
            if self._matches(rule, vector_count, dimension):
                matched_rule = rule
                break

        # 2. 推断度量类型
        metric_type = self._infer_metric_type(embedding_model)

        # 3. 输出推荐
        if matched_rule:
            reason = matched_rule.reason_template.format(
                count=vector_count, dim=dimension, model=embedding_model or "未知模型"
            )
            full_reason = (
                f"基于 {embedding_model or '未知模型'} {dimension}维 + "
                f"{vector_count}条向量推荐 — {reason}"
            )
            return {
                "index_type": matched_rule.recommended_index_type,
                "metric_type": matched_rule.recommended_metric_type or metric_type,
                "reason": full_reason,
                "is_fallback": False,
                "vector_count": vector_count,
                "dimension": dimension,
                "embedding_model": embedding_model,
            }

        # 4. 兜底
        return {
            "index_type": self.fallback["index_type"],
            "metric_type": self.fallback["metric_type"],
            "reason": self.fallback["reason"],
            "is_fallback": True,
            "vector_count": vector_count,
            "dimension": dimension,
            "embedding_model": embedding_model,
        }

    def _matches(
        self, rule: RecommendationRuleConfig, count: int, dim: int
    ) -> bool:
        """检查规则是否匹配"""
        if rule.min_vector_count is not None and count < rule.min_vector_count:
            return False
        if rule.max_vector_count is not None and count > rule.max_vector_count:
            return False
        if rule.min_dimension is not None and dim < rule.min_dimension:
            return False
        if rule.max_dimension is not None and dim > rule.max_dimension:
            return False
        return True

    def _infer_metric_type(self, model: str) -> str:
        """根据模型名称推断度量类型"""
        model_lower = (model or "").lower()
        for prefix, metric in self.metric_type_rules.items():
            if prefix != "default" and prefix in model_lower:
                return metric
        return self.metric_type_rules.get("default", "L2")


# ==================== 推荐行为日志服务 ====================


class RecommendationLogService:
    """推荐行为日志记录与统计"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def log_recommendation(
        self,
        embedding_task_id: str,
        recommended_index_type: str,
        recommended_metric_type: str,
        final_index_type: str,
        final_metric_type: str,
        is_fallback: bool = False,
        reason: str = "",
    ) -> RecommendationLog:
        """
        记录推荐采纳行为

        Args:
            embedding_task_id: 向量化任务ID
            recommended_index_type: 推荐的索引算法
            recommended_metric_type: 推荐的度量类型
            final_index_type: 用户最终选择的索引算法
            final_metric_type: 用户最终选择的度量类型
            is_fallback: 是否使用了兜底默认值
            reason: 推荐理由文案

        Returns:
            RecommendationLog 对象
        """
        is_modified = (
            recommended_index_type != final_index_type
            or recommended_metric_type != final_metric_type
        )

        log_entry = RecommendationLog(
            embedding_task_id=embedding_task_id,
            recommended_index_type=recommended_index_type,
            recommended_metric_type=recommended_metric_type,
            final_index_type=final_index_type,
            final_metric_type=final_metric_type,
            is_modified=is_modified,
            is_fallback=is_fallback,
            reason=reason or "",
        )

        try:
            self.db.add(log_entry)
            self.db.commit()
            self.db.refresh(log_entry)
            logger.info(
                f"推荐行为已记录: task={embedding_task_id}, "
                f"recommended={recommended_index_type}/{recommended_metric_type}, "
                f"final={final_index_type}/{final_metric_type}, "
                f"modified={is_modified}"
            )
            return log_entry
        except Exception as e:
            self.db.rollback()
            logger.error(f"记录推荐行为失败: {e}")
            raise

    def get_recommendation_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取推荐采纳率统计

        Args:
            days: 统计天数（默认30天）

        Returns:
            统计结果字典
        """
        cutoff_time = datetime.now() - timedelta(days=days)

        try:
            logs = (
                self.db.query(RecommendationLog)
                .filter(RecommendationLog.created_at >= cutoff_time)
                .all()
            )

            total = len(logs)
            if total == 0:
                return {
                    "total_recommendations": 0,
                    "adopted_count": 0,
                    "modified_count": 0,
                    "adoption_rate": 0.0,
                    "fallback_count": 0,
                    "period_days": days,
                }

            adopted = sum(1 for log in logs if not log.is_modified)
            modified = sum(1 for log in logs if log.is_modified)
            fallback = sum(1 for log in logs if log.is_fallback)

            return {
                "total_recommendations": total,
                "adopted_count": adopted,
                "modified_count": modified,
                "adoption_rate": round(adopted / total, 4) if total > 0 else 0.0,
                "fallback_count": fallback,
                "period_days": days,
            }

        except Exception as e:
            logger.error(f"获取推荐统计失败: {e}")
            return {
                "total_recommendations": 0,
                "adopted_count": 0,
                "modified_count": 0,
                "adoption_rate": 0.0,
                "fallback_count": 0,
                "period_days": days,
                "error": str(e),
            }


# ==================== 全局实例 ====================

_recommendation_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine(config_path: Optional[str] = None) -> RecommendationEngine:
    """获取推荐引擎全局实例"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine(config_path)
    return _recommendation_engine


def get_recommendation_log_service(db_session: Session) -> RecommendationLogService:
    """获取推荐日志服务实例"""
    return RecommendationLogService(db_session)
