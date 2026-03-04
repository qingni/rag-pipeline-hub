"""
查询增强服务 (Query Enhancement Service)

提供查询改写 (Query Rewrite) 和多查询生成 (Multi-query) 功能，
通过一次 LLM 调用同时完成，减少延迟。

设计理念：
- Query Rewrite（必选）：补全用户问题的上下文，使语义更清晰
- Multi-query（可选）：对复杂问题生成 2-3 个变体查询，覆盖不同表述

参考业内最佳实践：
- LangChain MultiQueryRetriever：LLM 生成多查询变体，合并去重
- LlamaIndex QueryTransformEngine：查询改写 + 子问题分解
- Cohere search_queries_only：一次调用生成多个搜索查询
- Google Vertex AI Search：自动查询改写和扩展
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger("query_enhancement")


# ==================== Prompt 模板 ====================

QUERY_ENHANCEMENT_SYSTEM_PROMPT = """你是一个专业的搜索查询优化助手。你的任务是对用户的原始查询进行改写和扩展，以提升在知识库中的检索效果。

## 你的工作流程

### 第一步：Query Rewrite（查询改写）
对用户的原始查询进行改写，使其语义更清晰、更适合向量检索：
- 补全省略的上下文，使查询自包含
- 将口语化表达转换为更正式、更精确的描述
- 保留用户查询的核心意图，不要添加用户未提及的限制条件
- 如果原始查询已经足够清晰，保持原意的同时进行微调即可

### 第二步：Multi-query（多查询生成）
判断原始查询是否需要多角度检索：
- **需要 multi-query 的情况**：查询涉及多个方面、查询较为宽泛、或同一概念有多种表述方式
- **不需要 multi-query 的情况**：查询已经非常具体明确，只指向单一信息

如果需要，生成 2-3 个查询变体，每个变体应从不同角度或使用不同表述来描述同一信息需求。

## 输出格式
请严格按以下 JSON 格式输出，不要输出其他内容：
```json
{
  "rewritten_query": "改写后的主查询",
  "is_complex": true/false,
  "sub_queries": ["变体查询1", "变体查询2"]
}
```

注意：
- `rewritten_query` 是必选字段，始终填写改写后的查询
- `is_complex` 为 false 时，`sub_queries` 为空数组 []
- `is_complex` 为 true 时，`sub_queries` 包含 2-3 个变体查询
- 变体查询不应与 rewritten_query 重复"""


QUERY_ENHANCEMENT_USER_PROMPT = """请对以下用户查询进行优化：

原始查询：{query_text}"""


QUERY_ENHANCEMENT_USER_PROMPT_WITH_CONTEXT = """请对以下用户查询进行优化：

对话历史：
{chat_history}

当前查询：{query_text}

注意：结合对话历史补全当前查询中省略的指代和上下文。"""


# ==================== 数据模型 ====================

@dataclass
class QueryEnhancementResult:
    """查询增强结果"""
    original_query: str                          # 原始查询
    rewritten_query: str                         # 改写后的主查询
    is_complex: bool = False                     # 是否为复杂查询
    sub_queries: List[str] = field(default_factory=list)  # 变体查询列表
    all_queries: List[str] = field(default_factory=list)  # 所有需要执行的查询（rewritten_query + sub_queries）
    enhancement_time_ms: int = 0                 # 查询增强耗时（毫秒）
    error: Optional[str] = None                  # 错误信息（如有）
    
    def __post_init__(self):
        """自动构建 all_queries 列表"""
        if not self.all_queries:
            self.all_queries = [self.rewritten_query]
            if self.is_complex and self.sub_queries:
                self.all_queries.extend(self.sub_queries)


# ==================== 查询增强服务 ====================

class QueryEnhancementService:
    """
    查询增强服务
    
    通过一次 LLM 调用同时完成 Query Rewrite 和 Multi-query 判断，
    减少延迟开销。
    
    使用方式：
        service = QueryEnhancementService()
        result = await service.enhance_query("交易页面中有哪些功能")
        # result.rewritten_query = "交易功能页面包含哪些功能按钮和交互元素"
        # result.all_queries = ["交易功能页面包含哪些功能按钮和交互元素", "交易功能页面的功能列表", ...]
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        request_timeout: int = 30,
    ):
        """
        初始化查询增强服务
        
        Args:
            api_key: LLM API Key（默认使用 EMBEDDING_API_KEY，与 GenerationService 一致）
            base_url: LLM API Base URL
            model: LLM 模型名称（默认使用 QUERY_ENHANCEMENT_MODEL 配置）
            temperature: 温度参数（查询改写需要精确性，默认 0.3）
            max_tokens: 最大输出 token 数（JSON 输出无需太大）
            request_timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = base_url or settings.EMBEDDING_API_BASE_URL
        self.model = model or getattr(settings, 'QUERY_ENHANCEMENT_MODEL', 'qwen3.5-35b-a3b')
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        
        self._llm_client: Optional[ChatOpenAI] = None
        
        logger.info(
            f"QueryEnhancementService 初始化: model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )
    
    @property
    def llm_client(self) -> ChatOpenAI:
        """获取 LLM 客户端（延迟初始化）"""
        if self._llm_client is None:
            self._llm_client = ChatOpenAI(
                model=self.model,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=False,  # 查询增强需要完整 JSON，不用流式
                request_timeout=self.request_timeout,
                max_retries=2,
                # 显式关闭思考模式：查询增强是简单的 JSON 结构化输出任务，
                # 不需要 CoT 推理。qwen3.5 系列默认开启思考模式会产生大量
                # thinking tokens，导致耗时从 ~3s 暴增到 ~20s
                # 参数说明：chat_template_kwargs.enable_thinking = false 关闭思考模式
                model_kwargs={"extra_body": {"chat_template_kwargs": {"enable_thinking": False}}},
            )
            logger.info(f"LLM 客户端初始化完成: model={self.model}")
        return self._llm_client
    
    async def enhance_query(
        self,
        query_text: str,
        chat_history: Optional[str] = None,
    ) -> QueryEnhancementResult:
        """
        执行查询增强：Query Rewrite + Multi-query（一次 LLM 调用）
        
        Args:
            query_text: 原始查询文本
            chat_history: 对话历史（可选，用于多轮对话场景中的指代消解）
            
        Returns:
            QueryEnhancementResult 包含改写后的查询和变体查询
        """
        start_time = time.time()
        
        try:
            # 构建 prompt
            if chat_history:
                user_prompt = QUERY_ENHANCEMENT_USER_PROMPT_WITH_CONTEXT.format(
                    query_text=query_text,
                    chat_history=chat_history
                )
            else:
                user_prompt = QUERY_ENHANCEMENT_USER_PROMPT.format(
                    query_text=query_text
                )
            
            messages = [
                SystemMessage(content=QUERY_ENHANCEMENT_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            
            # 调用 LLM
            logger.info(f"查询增强开始: original_query='{query_text}', model={self.model}")
            response = await self.llm_client.ainvoke(messages)
            
            # 解析 JSON 响应
            result = self._parse_response(response.content, query_text)
            result.enhancement_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"查询增强完成: original='{query_text}' → rewritten='{result.rewritten_query}', "
                f"is_complex={result.is_complex}, sub_queries={result.sub_queries}, "
                f"all_queries_count={len(result.all_queries)}, "
                f"耗时={result.enhancement_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            enhancement_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"查询增强失败，降级使用原始查询: error={str(e)}, "
                f"original_query='{query_text}', 耗时={enhancement_time_ms}ms"
            )
            # 降级：返回原始查询，不影响后续检索流程
            return QueryEnhancementResult(
                original_query=query_text,
                rewritten_query=query_text,
                is_complex=False,
                sub_queries=[],
                all_queries=[query_text],
                enhancement_time_ms=enhancement_time_ms,
                error=str(e)
            )
    
    def _parse_response(self, response_text: str, original_query: str) -> QueryEnhancementResult:
        """
        解析 LLM 返回的 JSON 响应
        
        支持多种格式的 JSON 提取（LLM 有时会在 JSON 前后添加 markdown 代码块标记）
        
        Args:
            response_text: LLM 返回的原始文本
            original_query: 原始查询（用于降级）
            
        Returns:
            QueryEnhancementResult
        """
        try:
            # 尝试直接解析 JSON
            json_str = response_text.strip()
            
            # 去除可能的 markdown 代码块标记
            if json_str.startswith("```"):
                # 去除 ```json 或 ``` 开头
                lines = json_str.split("\n")
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                json_str = "\n".join(lines[start_idx:end_idx])
            
            data = json.loads(json_str)
            
            rewritten_query = data.get("rewritten_query", "").strip()
            is_complex = data.get("is_complex", False)
            sub_queries = data.get("sub_queries", [])
            
            # 验证必要字段
            if not rewritten_query:
                logger.warning("LLM 返回的 rewritten_query 为空，使用原始查询")
                rewritten_query = original_query
            
            # 验证 sub_queries 格式
            if not isinstance(sub_queries, list):
                sub_queries = []
            sub_queries = [q.strip() for q in sub_queries if isinstance(q, str) and q.strip()]
            
            # 如果不复杂但给了 sub_queries，清空之
            if not is_complex:
                sub_queries = []
            
            # 构建结果
            all_queries = [rewritten_query]
            if is_complex and sub_queries:
                all_queries.extend(sub_queries)
            
            return QueryEnhancementResult(
                original_query=original_query,
                rewritten_query=rewritten_query,
                is_complex=is_complex,
                sub_queries=sub_queries,
                all_queries=all_queries,
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                f"解析 LLM 响应失败: error={str(e)}, response='{response_text[:200]}', "
                f"降级使用原始查询"
            )
            return QueryEnhancementResult(
                original_query=original_query,
                rewritten_query=original_query,
                is_complex=False,
                sub_queries=[],
                all_queries=[original_query],
                error=f"JSON 解析失败: {str(e)}"
            )
