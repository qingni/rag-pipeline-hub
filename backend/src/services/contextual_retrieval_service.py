"""Contextual Retrieval service for generating chunk-level context.

Implements Anthropic's Contextual Retrieval approach:
for each chunk, call an LLM with the full document + chunk to generate
a short context description that situates the chunk within the document.
This context is prepended to the chunk before embedding and BM25 indexing,
improving retrieval accuracy by ~49% (Anthropic benchmark).

Reference: https://www.anthropic.com/news/contextual-retrieval
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from ..config import settings

logger = logging.getLogger("contextual_retrieval")

DOCUMENT_CONTEXT_PROMPT = """<document>
{doc_content}
</document>"""

CHUNK_CONTEXT_PROMPT = """以下是需要在整个文档中定位上下文的文本片段：
<chunk>
{chunk_content}
</chunk>

请用1-2句简短的中文描述这个片段在整个文档中的位置和角色，用于帮助搜索引擎理解该片段的上下文。
只输出描述，不要其他内容。"""


class ContextualRetrievalService:
    """为每个 chunk 生成文档级上下文描述，提升检索精度。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 128,
        request_timeout: int = 30,
        max_workers: int = 5,
    ):
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = base_url or settings.EMBEDDING_API_BASE_URL
        self.model = model or getattr(settings, "CONTEXTUAL_RETRIEVAL_MODEL", "qwen3.5-35b-a3b")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.max_workers = max_workers
        self._llm_client: Optional[ChatOpenAI] = None

        logger.info(
            f"ContextualRetrievalService initialized: model={self.model}, "
            f"max_workers={self.max_workers}"
        )

    @property
    def llm_client(self) -> ChatOpenAI:
        if self._llm_client is None:
            self._llm_client = ChatOpenAI(
                model=self.model,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=False,
                request_timeout=self.request_timeout,
                max_retries=2,
                model_kwargs={
                    "extra_body": {
                        "chat_template_kwargs": {"enable_thinking": False}
                    }
                },
            )
            logger.info(f"LLM client initialized: model={self.model}")
        return self._llm_client

    def _generate_single_context(self, doc_content: str, chunk_content: str) -> str:
        """为单个 chunk 生成上下文描述。"""
        prompt = (
            DOCUMENT_CONTEXT_PROMPT.format(doc_content=doc_content)
            + "\n"
            + CHUNK_CONTEXT_PROMPT.format(chunk_content=chunk_content)
        )
        try:
            response = self.llm_client.invoke([HumanMessage(content=prompt)])
            context = response.content.strip()
            return context
        except Exception as e:
            logger.warning(f"Failed to generate context for chunk (len={len(chunk_content)}): {e}")
            return ""

    def generate_chunk_contexts(
        self,
        full_doc_text: str,
        chunk_contents: List[str],
    ) -> List[str]:
        """
        为一组 chunks 批量生成上下文描述。

        使用 ThreadPoolExecutor 并发调用 LLM，同一文档的所有 chunk
        共享相同的 doc_content 输入。

        Args:
            full_doc_text: 完整的文档原文
            chunk_contents: 每个 chunk 的文本内容列表

        Returns:
            与 chunk_contents 等长的上下文描述列表，生成失败的返回空字符串
        """
        num_chunks = len(chunk_contents)
        if num_chunks == 0:
            return []

        logger.info(
            f"Generating contextual descriptions: {num_chunks} chunks, "
            f"doc_length={len(full_doc_text)} chars, max_workers={self.max_workers}"
        )
        start_time = time.time()

        # 保持顺序的结果数组
        contexts: List[str] = [""] * num_chunks

        workers = min(self.max_workers, num_chunks)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(
                    self._generate_single_context, full_doc_text, chunk_content
                ): i
                for i, chunk_content in enumerate(chunk_contents)
            }

            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    contexts[idx] = future.result()
                except Exception as e:
                    logger.warning(f"Chunk {idx} context generation failed: {e}")
                    contexts[idx] = ""
                completed += 1
                if completed % 10 == 0 or completed == num_chunks:
                    logger.info(f"Context generation progress: {completed}/{num_chunks}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        success_count = sum(1 for c in contexts if c)
        logger.info(
            f"Contextual retrieval completed: {success_count}/{num_chunks} succeeded, "
            f"elapsed={elapsed_ms}ms"
        )

        return contexts

    @staticmethod
    def prepend_context(context: str, chunk_text: str) -> str:
        """将生成的上下文描述拼接到 chunk 文本前面。"""
        if not context:
            return chunk_text
        return f"{context}\n{chunk_text}"
