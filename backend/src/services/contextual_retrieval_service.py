"""Contextual Retrieval service for generating chunk-level context.

Implements Anthropic's Contextual Retrieval approach:
for a batch of chunks, call an LLM with the full document + chunk batch
to generate short context descriptions that situate chunks in document scope.
These contexts are prepended to chunks before embedding and BM25 indexing.

Reference: https://www.anthropic.com/news/contextual-retrieval
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ..config import settings

logger = logging.getLogger("contextual_retrieval")

DOCUMENT_CONTEXT_PROMPT = """<document>
{doc_content}
</document>"""

BATCH_CHUNK_CONTEXT_PROMPT = """以下是需要在整个文档中定位上下文的文本片段列表：
{chunk_blocks}

请为每个片段输出1-2句简短中文描述，说明该片段在文档中的位置和作用。

输出要求（必须严格遵守）：
1. 只输出 JSON，不要输出 Markdown 代码块，不要输出任何解释文字
2. JSON 格式必须是数组
3. 每个元素包含两个字段：chunk_id（整数）、context（字符串）
4. 必须覆盖输入中的每个 chunk_id，且每个 chunk_id 只能出现一次

示例输出：
[
  {"chunk_id": 0, "context": "该片段位于文档开头，介绍背景与目标。"},
  {"chunk_id": 1, "context": "该片段在方法章节，描述关键实现步骤。"}
]"""


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
        batch_size: int = 10,
    ):
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = base_url or settings.EMBEDDING_API_BASE_URL
        self.model = model or getattr(settings, "CONTEXTUAL_RETRIEVAL_MODEL", "qwen3.5-35b-a3b")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.max_workers = max_workers
        self.batch_size = max(1, batch_size)
        self._llm_client: Optional[ChatOpenAI] = None

        logger.info(
            f"ContextualRetrievalService initialized: model={self.model}, "
            f"max_workers={self.max_workers}, batch_size={self.batch_size}"
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

    def _build_batch_prompt(
        self,
        doc_content: str,
        batch_items: Sequence[Tuple[int, str]],
    ) -> str:
        chunk_blocks = []
        for chunk_id, chunk_content in batch_items:
            chunk_blocks.append(
                f"<chunk id=\"{chunk_id}\">\n{chunk_content}\n</chunk>"
            )
        return (
            DOCUMENT_CONTEXT_PROMPT.format(doc_content=doc_content)
            + "\n"
            + BATCH_CHUNK_CONTEXT_PROMPT.format(chunk_blocks="\n\n".join(chunk_blocks))
        )

    @staticmethod
    def _normalize_response_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
                elif item is not None:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped

        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return stripped

    def _extract_json_payload(self, text: str) -> str:
        normalized = self._strip_markdown_fence(text)

        array_start = normalized.find("[")
        array_end = normalized.rfind("]")
        if array_start != -1 and array_end != -1 and array_end > array_start:
            return normalized[array_start:array_end + 1]

        obj_start = normalized.find("{")
        obj_end = normalized.rfind("}")
        if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
            return normalized[obj_start:obj_end + 1]

        return normalized

    def _parse_batch_contexts(
        self,
        response_text: str,
        expected_ids: Sequence[int],
    ) -> Dict[int, str]:
        payload = self._extract_json_payload(response_text)
        data = json.loads(payload)

        if isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = data.get("items") or data.get("results") or []
        else:
            entries = []

        expected_set = set(expected_ids)
        parsed: Dict[int, str] = {}
        for item in entries:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("chunk_id", item.get("id", item.get("index")))
            if raw_id is None:
                continue

            try:
                chunk_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if chunk_id not in expected_set:
                continue

            context = str(item.get("context", "")).strip()
            if context:
                parsed[chunk_id] = context

        return parsed

    def _generate_batch_contexts(
        self,
        doc_content: str,
        batch_items: Sequence[Tuple[int, str]],
    ) -> Dict[int, str]:
        expected_ids = [chunk_id for chunk_id, _ in batch_items]
        prompt = self._build_batch_prompt(doc_content, batch_items)

        try:
            response = self.llm_client.invoke([HumanMessage(content=prompt)])
            response_text = self._normalize_response_content(response.content)
            parsed_contexts = self._parse_batch_contexts(response_text, expected_ids)

            if len(parsed_contexts) < len(expected_ids):
                logger.warning(
                    "Context batch partially parsed: parsed=%s/%s, ids=%s",
                    len(parsed_contexts),
                    len(expected_ids),
                    expected_ids,
                )

            return parsed_contexts
        except Exception as exc:
            logger.warning(
                "Failed to generate context batch (size=%s, ids=%s): %s",
                len(batch_items),
                expected_ids,
                exc,
            )
            return {}

    def generate_chunk_contexts(
        self,
        full_doc_text: str,
        chunk_contents: List[str],
    ) -> List[str]:
        """
        为一组 chunks 批量生成上下文描述。

        与旧实现相比：按 batch 调用 LLM（一次请求处理多个 chunks），
        避免「1 chunk = 1 请求」导致的请求数膨胀。
        """
        num_chunks = len(chunk_contents)
        if num_chunks == 0:
            return []

        indexed_chunks: List[Tuple[int, str]] = list(enumerate(chunk_contents))
        chunk_batches: List[List[Tuple[int, str]]] = [
            indexed_chunks[i:i + self.batch_size]
            for i in range(0, num_chunks, self.batch_size)
        ]
        num_batches = len(chunk_batches)

        logger.info(
            "Generating contextual descriptions: chunks=%s, batches=%s, batch_size=%s, "
            "doc_length=%s chars, max_workers=%s",
            num_chunks,
            num_batches,
            self.batch_size,
            len(full_doc_text),
            self.max_workers,
        )
        start_time = time.time()

        # 保持顺序的结果数组
        contexts: List[str] = [""] * num_chunks

        workers = min(self.max_workers, num_batches)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {
                executor.submit(
                    self._generate_batch_contexts,
                    full_doc_text,
                    batch_items,
                ): batch_items
                for batch_items in chunk_batches
            }

            completed_chunks = 0
            for future in as_completed(future_to_batch):
                batch_items = future_to_batch[future]
                batch_contexts: Dict[int, str] = {}
                try:
                    batch_contexts = future.result()
                except Exception as exc:
                    first_id = batch_items[0][0] if batch_items else -1
                    logger.warning(
                        "Context batch future failed (first_chunk_id=%s): %s",
                        first_id,
                        exc,
                    )

                for chunk_id, _ in batch_items:
                    contexts[chunk_id] = batch_contexts.get(chunk_id, "")

                completed_chunks += len(batch_items)
                if completed_chunks % 10 == 0 or completed_chunks == num_chunks:
                    logger.info(
                        "Context generation progress: %s/%s",
                        completed_chunks,
                        num_chunks,
                    )

        elapsed_ms = int((time.time() - start_time) * 1000)
        success_count = sum(1 for c in contexts if c)
        logger.info(
            "Contextual retrieval completed: %s/%s succeeded, batches=%s, elapsed=%sms",
            success_count,
            num_chunks,
            num_batches,
            elapsed_ms,
        )

        return contexts

    @staticmethod
    def prepend_context(context: str, chunk_text: str) -> str:
        """将生成的上下文描述拼接到 chunk 文本前面。"""
        if not context:
            return chunk_text
        return f"{context}\n{chunk_text}"
