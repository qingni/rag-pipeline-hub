"""Generation service for RAG text generation."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from ..config import settings
from ..models.generation import GenerationHistory, GenerationStatus
from ..schemas.generation import (
    ContextItem,
    GenerationRequest,
    TokenUsage,
    SourceReference,
)


# ============== Model Configuration ==============

GENERATION_MODELS: Dict[str, Dict[str, Any]] = {
    "deepseek-v3": {
        "name": "deepseek-v3",
        "context_length": 128000,
        "description": "DeepSeek V3 - 0324最新版本，稳定可靠",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "deepseek-r1": {
        "name": "deepseek-r1",
        "context_length": 128000,
        "description": "DeepSeek R1 - 支持 Function Calling，128K超长上下文",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
    "kimi-k2-instruct": {
        "name": "kimi-k2-instruct",
        "context_length": 128000,
        "description": "Kimi K2 Instruct - 1TB参数，即插即用",
        "default_temperature": 0.7,
        "default_max_tokens": 4096,
    },
}

# Default prompt template
SYSTEM_PROMPT_TEMPLATE = """你是一个智能问答助手。请基于以下参考资料回答用户的问题。

## 参考资料

{context}

## 回答要求

1. 基于参考资料给出准确、详细的回答
2. 如果引用了某段资料，请在回答中标注来源编号，如 [1]、[2]
3. 如果参考资料不足以回答问题，请明确说明
4. 回答应该条理清晰，易于理解"""

SYSTEM_PROMPT_NO_CONTEXT = """你是一个智能问答助手。请根据你的知识回答用户的问题。

## 回答要求

1. 给出准确、详细的回答
2. 如果不确定答案，请明确说明
3. 回答应该条理清晰，易于理解"""


@dataclass
class GenerationResult:
    """Result of a generation request."""
    request_id: str
    answer: str
    model: str
    token_usage: TokenUsage
    processing_time_ms: float
    sources: List[SourceReference]


class GenerationError(Exception):
    """Base exception for generation errors."""
    pass


class ModelNotFoundError(GenerationError):
    """Raised when model is not found."""
    pass


class GenerationCancelledError(GenerationError):
    """Raised when generation is cancelled."""
    pass


class GenerationService:
    """Service for text generation using LLM models."""
    
    # Track active generation requests for cancellation
    _active_requests: Dict[str, bool] = {}
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        request_timeout: int = 120,
    ) -> None:
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.base_url = base_url or settings.EMBEDDING_API_BASE_URL
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        
        if not self.api_key:
            raise ValueError("API key is required for generation service")
        if not self.base_url:
            raise ValueError("Base URL is required for generation service")
    
    def _get_llm_client(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        streaming: bool = False,
    ) -> ChatOpenAI:
        """Initialize ChatOpenAI client for the specified model."""
        if model not in GENERATION_MODELS:
            raise ModelNotFoundError(f"Model '{model}' not found. Available models: {list(GENERATION_MODELS.keys())}")
        
        return ChatOpenAI(
            model=model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            request_timeout=self.request_timeout,
            max_retries=self.max_retries,
        )
    
    def _build_prompt(
        self,
        question: str,
        context: List[ContextItem],
    ) -> tuple[str, str]:
        """Build system and user prompts from question and context.
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        if not context:
            # No context mode
            return SYSTEM_PROMPT_NO_CONTEXT, question
        
        # Build context string
        context_parts = []
        for i, item in enumerate(context, 1):
            context_parts.append(f"[{i}] {item.content}\n来源：{item.source_file}")
        
        context_str = "\n\n".join(context_parts)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context_str)
        
        return system_prompt, question
    
    def _extract_sources(self, context: List[ContextItem]) -> List[SourceReference]:
        """Extract source references from context items."""
        return [
            SourceReference(
                index=i + 1,
                source_file=item.source_file,
                similarity=item.similarity
            )
            for i, item in enumerate(context)
        ]
    
    def _validate_request(self, request: GenerationRequest) -> None:
        """Validate generation request parameters."""
        if request.model not in GENERATION_MODELS:
            raise ModelNotFoundError(
                f"Model '{request.model}' not supported. "
                f"Available models: {list(GENERATION_MODELS.keys())}"
            )
        
        model_info = GENERATION_MODELS[request.model]
        
        # Check context length (rough estimate: 4 chars per token)
        total_context_length = sum(len(item.content) for item in request.context)
        estimated_tokens = total_context_length // 4 + len(request.question) // 4
        
        if estimated_tokens > model_info["context_length"] * 0.8:
            raise GenerationError(
                f"Context too long. Estimated {estimated_tokens} tokens, "
                f"model supports {model_info['context_length']} tokens"
            )
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text response (non-streaming).
        
        Args:
            request: Generation request with question, model, and context
            
        Returns:
            GenerationResult with answer and metadata
        """
        self._validate_request(request)
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Build prompts
        system_prompt, user_prompt = self._build_prompt(
            request.question,
            request.context
        )
        
        # Initialize client
        llm = self._get_llm_client(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            streaming=False,
        )
        
        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        # Generate response
        try:
            response = await llm.ainvoke(messages)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Extract token usage
            token_usage = TokenUsage(
                prompt_tokens=response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                completion_tokens=response.response_metadata.get("token_usage", {}).get("completion_tokens", 0),
                total_tokens=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            )
            
            return GenerationResult(
                request_id=request_id,
                answer=response.content,
                model=request.model,
                token_usage=token_usage,
                processing_time_ms=processing_time_ms,
                sources=self._extract_sources(request.context),
            )
        except Exception as e:
            raise GenerationError(f"Generation failed: {str(e)}") from e
    
    async def generate_stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate text response with streaming.
        
        Args:
            request: Generation request with question, model, and context
            
        Yields:
            Dict with content chunks and metadata
        """
        self._validate_request(request)
        
        request_id = str(uuid.uuid4())
        self._active_requests[request_id] = True
        
        start_time = time.time()
        total_content = ""
        
        try:
            # Build prompts
            system_prompt, user_prompt = self._build_prompt(
                request.question,
                request.context
            )
            
            # Initialize streaming client
            llm = self._get_llm_client(
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                streaming=True,
            )
            
            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            # Yield initial chunk with request_id
            yield {
                "request_id": request_id,
                "content": "",
                "done": False,
            }
            
            # Stream response
            async for chunk in llm.astream(messages):
                # Check for cancellation
                if not self._active_requests.get(request_id, False):
                    raise GenerationCancelledError("Generation cancelled by user")
                
                content = chunk.content if hasattr(chunk, 'content') else ""
                if content:
                    total_content += content
                    yield {
                        "content": content,
                        "done": False,
                    }
            
            # Final chunk with token usage
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Estimate token usage for streaming (actual usage not always available)
            estimated_prompt_tokens = len(system_prompt + user_prompt) // 4
            estimated_completion_tokens = len(total_content) // 4
            
            yield {
                "content": "",
                "done": True,
                "token_usage": {
                    "prompt_tokens": estimated_prompt_tokens,
                    "completion_tokens": estimated_completion_tokens,
                    "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                },
                "processing_time_ms": processing_time_ms,
                "sources": [s.model_dump() for s in self._extract_sources(request.context)],
            }
            
        except GenerationCancelledError:
            yield {
                "content": "",
                "done": True,
                "cancelled": True,
            }
        except Exception as e:
            yield {
                "content": "",
                "done": True,
                "error": str(e),
            }
        finally:
            self._active_requests.pop(request_id, None)
    
    def cancel_generation(self, request_id: str) -> bool:
        """Cancel an active generation request.
        
        Args:
            request_id: The request ID to cancel
            
        Returns:
            True if request was found and cancelled, False otherwise
        """
        if request_id in self._active_requests:
            self._active_requests[request_id] = False
            return True
        return False
    
    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """Get list of available generation models."""
        return [
            {
                "name": info["name"],
                "context_length": info["context_length"],
                "description": info["description"],
                "default_temperature": info["default_temperature"],
                "default_max_tokens": info["default_max_tokens"],
            }
            for info in GENERATION_MODELS.values()
        ]
    
    @staticmethod
    def get_model_info(model: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific model."""
        if model not in GENERATION_MODELS:
            return None
        info = GENERATION_MODELS[model]
        return {
            "name": info["name"],
            "context_length": info["context_length"],
            "description": info["description"],
            "default_temperature": info["default_temperature"],
            "default_max_tokens": info["default_max_tokens"],
        }
    
    @staticmethod
    def cleanup_old_history(db_session, max_records: int = 100) -> int:
        """Clean up old history records when exceeding max limit.
        
        Args:
            db_session: Database session
            max_records: Maximum number of records to keep
            
        Returns:
            Number of records deleted
        """
        from sqlalchemy import func
        
        # Count non-deleted records
        count = db_session.query(func.count(GenerationHistory.id)).filter(
            GenerationHistory.is_deleted == False
        ).scalar()
        
        if count <= max_records:
            return 0
        
        # Get IDs of oldest records to delete
        records_to_delete = count - max_records
        oldest_records = db_session.query(GenerationHistory.id).filter(
            GenerationHistory.is_deleted == False
        ).order_by(GenerationHistory.created_at.asc()).limit(records_to_delete).all()
        
        ids_to_delete = [r[0] for r in oldest_records]
        
        # Soft delete old records
        db_session.query(GenerationHistory).filter(
            GenerationHistory.id.in_(ids_to_delete)
        ).update({"is_deleted": True}, synchronize_session=False)
        
        db_session.commit()
        
        return len(ids_to_delete)
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text (rough estimate: ~4 chars per token for Chinese/English mix)."""
        return len(text) // 4
    
    def check_context_length(self, request: GenerationRequest) -> dict:
        """Check if context length is within limits.
        
        Returns:
            Dict with 'valid' boolean and 'message' if invalid
        """
        model_info = GENERATION_MODELS.get(request.model)
        if not model_info:
            return {"valid": False, "message": f"Unknown model: {request.model}"}
        
        max_context = model_info["context_length"]
        
        # Calculate total tokens
        question_tokens = self.estimate_tokens(request.question)
        context_tokens = sum(self.estimate_tokens(item.content) for item in request.context)
        system_prompt_tokens = 500  # Approximate system prompt tokens
        
        total_tokens = question_tokens + context_tokens + system_prompt_tokens
        
        # Reserve space for output
        available_for_input = max_context - request.max_tokens
        
        if total_tokens > available_for_input * 0.9:  # 90% threshold
            return {
                "valid": False,
                "message": f"输入内容过长。预估 {total_tokens} tokens，"
                          f"模型最大支持 {available_for_input} tokens（保留 {request.max_tokens} 用于输出）。"
                          f"请缩短问题或减少上下文数量。",
                "estimated_tokens": total_tokens,
                "max_tokens": available_for_input,
            }
        
        return {"valid": True, "estimated_tokens": total_tokens}
