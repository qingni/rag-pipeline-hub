"""Semantic-based chunker implementation with unified EmbeddingService and TF-IDF fallback."""
from typing import List, Dict, Any, Optional
import re
import logging
import math
from .base_chunker import BaseChunker

logger = logging.getLogger(__name__)

# 支持的 Embedding 模型列表
SUPPORTED_EMBEDDING_MODELS = ['bge-m3', 'qwen3-embedding-8b']


class SemanticChunker(BaseChunker):
    """
    Chunker that splits text by semantic similarity.
    
    Strategy:
    1. Primary: Use unified EmbeddingService (bge-m3 / qwen3-embedding-8b)
    2. Fallback 1: TF-IDF similarity (no external API)
    3. Fallback 2: Sentence accumulation (simple)
    
    Supported embedding models:
    - bge-m3: 1024维，8K上下文，多语言，速度快（推荐）
    - qwen3-embedding-8b: 4096维，32K上下文，高精度
    """
    
    def __init__(self, **params):
        """
        Initialize semantic chunker with optional embedding model config.
        
        Supported params:
        - embedding_model: Model name (default: 'bge-m3')
            Options: 'bge-m3', 'qwen3-embedding-8b'
        - use_embedding: Enable/disable embedding (default: True)
        - similarity_threshold: Merge threshold for TF-IDF fallback (default: 0.3)
        - embedding_similarity_threshold: Merge threshold for embedding (default: 0.7)
        - min_chunk_size: Minimum chunk size (default: 300)
        - max_chunk_size: Maximum chunk size (default: 1200)
        """
        self._embedding_service = None
        self._use_embedding = params.get('use_embedding', True)
        self._embedding_model_name = params.get('embedding_model', 'bge-m3')
        self._embedding_similarity_threshold = params.get('embedding_similarity_threshold', 0.7)
        super().__init__(**params)
    
    def validate_params(self) -> None:
        """
        Validate semantic chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        threshold = self.params.get('similarity_threshold', 0.3)
        min_size = self.params.get('min_chunk_size', 300)
        
        if not isinstance(threshold, (int, float)) or threshold < 0.1 or threshold > 0.9:
            raise ValueError("similarity_threshold must be between 0.1 and 0.9")
        
        if not isinstance(min_size, int) or min_size <= 0:
            raise ValueError("min_chunk_size must be a positive integer")
        
        # Validate embedding model
        embedding_model = self.params.get('embedding_model', 'bge-m3')
        if embedding_model not in SUPPORTED_EMBEDDING_MODELS:
            logger.warning(
                f"Unsupported embedding model: {embedding_model}, "
                f"supported: {SUPPORTED_EMBEDDING_MODELS}. Using 'bge-m3' as default."
            )
    
    def _init_embedding_service(self) -> bool:
        """
        Initialize unified EmbeddingService.
        
        Uses the same EmbeddingService as document vectorization,
        supporting bge-m3, qwen3-embedding-8b.
        
        Returns:
            True if successful, False otherwise
        """
        if self._embedding_service is not None:
            return True
        
        try:
            from ...services.embedding_service import EmbeddingService
            from ...config import settings
            
            # Check API configuration
            if not settings.EMBEDDING_API_KEY or not settings.EMBEDDING_API_BASE_URL:
                logger.warning("Embedding API not configured, will use TF-IDF fallback")
                return False
            
            # Determine model to use
            model = self._embedding_model_name
            if model not in SUPPORTED_EMBEDDING_MODELS:
                model = 'bge-m3'
                logger.info(f"Using default model: {model}")
            
            # Initialize service with unified EmbeddingService
            self._embedding_service = EmbeddingService(
                api_key=settings.EMBEDDING_API_KEY,
                model=model,
                base_url=settings.EMBEDDING_API_BASE_URL,
                max_retries=3,
                request_timeout=60
            )
            
            logger.info(f"Initialized EmbeddingService with model: {model}")
            return True
            
        except ImportError as e:
            logger.warning(f"EmbeddingService not available: {e}, will use TF-IDF fallback")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize EmbeddingService: {e}, will use TF-IDF fallback")
            return False
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by semantic similarity.
        
        Strategy (priority order):
        1. Primary: Use unified EmbeddingService (bge-m3 / qwen3-embedding-8b)
        2. Fallback 1: TF-IDF similarity (no external API)
        3. Fallback 2: Sentence accumulation (simple)
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        if not text or len(text) == 0:
            return []
        
        threshold = self.params.get('similarity_threshold', 0.3)
        min_size = self.params.get('min_chunk_size', 300)
        max_size = self.params.get('max_chunk_size', 1200)
        
        # Try Embedding-based chunking first
        if self._use_embedding:
            try:
                return self._embedding_based_chunk(text, min_size, max_size)
            except Exception as e:
                logger.warning(f"Embedding-based chunking failed: {e}, falling back to TF-IDF")
        
        # Fallback to TF-IDF
        try:
            return self._tfidf_chunk(text, threshold, min_size, max_size)
        except Exception as e:
            logger.warning(f"TF-IDF chunking failed: {e}, falling back to sentence-based")
            return self._fallback_to_sentences(text, min_size)
    
    def _embedding_based_chunk(
        self, 
        text: str, 
        min_size: int, 
        max_size: int
    ) -> List[Dict[str, Any]]:
        """
        Chunk text using unified EmbeddingService with semantic similarity.
        
        Algorithm:
        1. Split text into sentences
        2. Get embeddings for each sentence via EmbeddingService
        3. Calculate cosine similarity between adjacent sentences
        4. Merge sentences with high similarity (> threshold)
        5. Respect min/max size constraints
        
        Args:
            text: Input text
            min_size: Minimum chunk size
            max_size: Maximum chunk size
        
        Returns:
            List of chunks
        """
        if not self._init_embedding_service():
            raise RuntimeError("EmbeddingService initialization failed")
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) < 2:
            # Not enough sentences for semantic analysis
            raise ValueError("Insufficient sentences for semantic chunking")
        
        # Get embeddings for all sentences via unified EmbeddingService
        try:
            batch_result = self._embedding_service.embed_documents(sentences)
            
            if not batch_result.vectors:
                raise RuntimeError("No embeddings returned from EmbeddingService")
            
            # Extract vectors (sorted by index)
            vectors = sorted(batch_result.vectors, key=lambda v: v.index)
            sentence_embeddings = [v.vector for v in vectors]
            
            # Log any failures
            if batch_result.failures:
                logger.warning(
                    f"Some sentences failed to embed: {len(batch_result.failures)} failures"
                )
            
        except Exception as e:
            logger.error(f"Failed to get embeddings from EmbeddingService: {e}")
            raise
        
        # Calculate similarity and group sentences
        chunks = []
        current_chunk_sentences = [sentences[0]]
        current_start = 0
        similarity_threshold = self._embedding_similarity_threshold
        
        for i in range(1, len(sentences)):
            # Skip if this sentence failed to embed
            if i >= len(sentence_embeddings):
                current_chunk_sentences.append(sentences[i])
                continue
            
            # Calculate cosine similarity with previous sentence
            similarity = self._cosine_similarity_vectors(
                sentence_embeddings[i-1], 
                sentence_embeddings[i]
            )
            
            current_length = sum(len(s) for s in current_chunk_sentences)
            next_length = current_length + len(sentences[i])
            
            # Decide whether to merge
            # High similarity and within max_size → merge
            # Or current chunk too small and adding won't exceed max_size * 1.2 → merge
            should_merge = (
                (similarity >= similarity_threshold and next_length <= max_size) or
                (current_length < min_size and next_length <= max_size * 1.2)
            )
            
            if should_merge:
                current_chunk_sentences.append(sentences[i])
            else:
                # Save current chunk
                content = ' '.join(current_chunk_sentences)
                start_pos = text.find(current_chunk_sentences[0], current_start)
                if start_pos == -1:
                    start_pos = current_start
                end_pos = start_pos + len(content)
                
                chunk = self._create_chunk(
                    content=content,
                    index=len(chunks),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    strategy="semantic",
                    chunking_method="embedding",
                    embedding_model=self._embedding_model_name,
                    sentence_count=len(current_chunk_sentences),
                    avg_similarity=similarity
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_chunk_sentences = [sentences[i]]
                current_start = end_pos
        
        # Add last chunk
        if current_chunk_sentences:
            content = ' '.join(current_chunk_sentences)
            start_pos = text.find(current_chunk_sentences[0], current_start)
            if start_pos == -1:
                start_pos = current_start
            
            chunk = self._create_chunk(
                content=content,
                index=len(chunks),
                start_pos=start_pos,
                end_pos=len(text),
                strategy="semantic",
                chunking_method="embedding",
                embedding_model=self._embedding_model_name,
                sentence_count=len(current_chunk_sentences)
            )
            chunks.append(chunk)
        
        # Handle edge case: only 1 chunk for long text
        if len(chunks) == 1 and len(text) > max_size * 1.5:
            logger.warning(
                f"Only 1 chunk generated for long text ({len(text)} chars), "
                "splitting by size constraints"
            )
            return self._split_single_chunk(chunks[0], min_size, max_size)
        
        logger.info(
            f"Embedding-based chunking produced {len(chunks)} chunks "
            f"using {self._embedding_model_name}"
        )
        return chunks
    
    @staticmethod
    def _cosine_similarity_vectors(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two embedding vectors."""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions mismatch: {len(vec1)} vs {len(vec2)}")
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = math.sqrt(sum(a * a for a in vec1))
        mag2 = math.sqrt(sum(b * b for b in vec2))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def _split_single_chunk(
        self,
        chunk: Dict[str, Any],
        min_size: int,
        max_size: int
    ) -> List[Dict[str, Any]]:
        """Split a single large chunk into multiple smaller chunks."""
        content = chunk['content']
        return self._split_large_chunk(
            content, 
            max_size, 
            chunk['metadata'].get('start_position', 0),
            0
        )
    
    def _split_large_chunk(
        self, 
        content: str, 
        max_size: int, 
        start_pos: int, 
        start_index: int
    ) -> List[Dict[str, Any]]:
        """Split a chunk that exceeds max_size into smaller chunks."""
        chunks = []
        sentences = self._split_sentences(content)
        
        current_content = []
        current_length = 0
        chunk_start = start_pos
        
        for sentence in sentences:
            if current_length + len(sentence) > max_size and current_content:
                # Save current chunk
                text = ' '.join(current_content)
                chunks.append(self._create_chunk(
                    content=text,
                    index=start_index + len(chunks),
                    start_pos=chunk_start,
                    end_pos=chunk_start + len(text),
                    strategy="semantic",
                    chunking_method="embedding_split"
                ))
                chunk_start = chunk_start + len(text)
                current_content = []
                current_length = 0
            
            current_content.append(sentence)
            current_length += len(sentence)
        
        # Don't forget the last chunk
        if current_content:
            text = ' '.join(current_content)
            chunks.append(self._create_chunk(
                content=text,
                index=start_index + len(chunks),
                start_pos=chunk_start,
                end_pos=chunk_start + len(text),
                strategy="semantic",
                chunking_method="embedding_split"
            ))
        
        return chunks
    
    def _tfidf_chunk(
        self,
        text: str,
        threshold: float,
        min_size: int,
        max_size: int
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic chunking using TF-IDF similarity (fallback method).
        
        Args:
            text: Input text
            threshold: Similarity threshold (0-1)
            min_size: Minimum chunk size in characters
            max_size: Maximum chunk size in characters
        
        Returns:
            List of chunks
        """
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) < 2:
            # Not enough sentences for semantic analysis
            raise ValueError("Insufficient sentences for semantic chunking")
        
        # Calculate TF-IDF vectors for sentences
        vectors = self._calculate_tfidf(sentences)
        
        # Group sentences by similarity
        chunks = []
        current_chunk_sentences = [sentences[0]]
        current_start = 0
        chunk_index = 0
        
        for i in range(1, len(sentences)):
            # Calculate similarity with previous sentence
            similarity = self._cosine_similarity(vectors[i-1], vectors[i])
            
            current_length = sum(len(s) for s in current_chunk_sentences)
            next_length = current_length + len(sentences[i])
            
            should_merge = False
            
            if similarity >= threshold and next_length <= max_size:
                should_merge = True
            elif current_length < min_size and next_length <= max_size * 1.5:
                should_merge = True
            
            if should_merge:
                current_chunk_sentences.append(sentences[i])
            else:
                content = ' '.join(current_chunk_sentences)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=text.find(current_chunk_sentences[0], current_start),
                    end_pos=text.find(current_chunk_sentences[-1], current_start) + len(current_chunk_sentences[-1]),
                    strategy="semantic",
                    chunking_method="tfidf",
                    sentence_count=len(current_chunk_sentences),
                    avg_similarity=similarity
                )
                chunks.append(chunk)
                chunk_index += 1
                current_start = text.find(sentences[i], current_start)
                current_chunk_sentences = [sentences[i]]
        
        # Add the last chunk
        if current_chunk_sentences:
            content = ' '.join(current_chunk_sentences)
            chunk = self._create_chunk(
                content=content,
                index=chunk_index,
                start_pos=text.find(current_chunk_sentences[0], current_start),
                end_pos=len(text),
                strategy="semantic",
                chunking_method="tfidf",
                sentence_count=len(current_chunk_sentences),
                avg_similarity=threshold
            )
            chunks.append(chunk)
        
        # If only 1 chunk generated for long text, try fallback
        if len(chunks) == 1 and len(text) > max_size * 1.5:
            logger.warning(f"Only 1 chunk generated for long text ({len(text)} chars), trying fallback")
            return self._fallback_to_sentences(text, min_size)
        
        logger.info(f"TF-IDF chunking produced {len(chunks)} chunks")
        return chunks
    
    def _fallback_to_sentences(self, text: str, min_size: int) -> List[Dict[str, Any]]:
        """
        Fallback to simple sentence-based chunking.
        
        Args:
            text: Input text
            min_size: Minimum chunk size
        
        Returns:
            List of chunks with fallback indicator
        """
        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        current_start = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length >= min_size and current_chunk:
                content = ' '.join(current_chunk)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=current_start,
                    end_pos=current_start + len(content),
                    strategy="semantic",
                    chunking_method="sentence_fallback",
                    sentence_count=len(current_chunk),
                    fallback_reason="semantic_analysis_failed"
                )
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = []
                current_length = 0
                current_start = text.find(sentence, current_start)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            content = ' '.join(current_chunk)
            chunk = self._create_chunk(
                content=content,
                index=chunk_index,
                start_pos=current_start,
                end_pos=len(text),
                strategy="semantic",
                chunking_method="sentence_fallback",
                sentence_count=len(current_chunk),
                fallback_reason="semantic_analysis_failed"
            )
            chunks.append(chunk)
        
        logger.info(f"Sentence fallback produced {len(chunks)} chunks")
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting for Chinese and English
        sentences = re.split(r'[。！？.!?]\s*', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_tfidf(self, sentences: List[str]) -> List[Dict[str, float]]:
        """
        Calculate TF-IDF vectors for sentences (simplified implementation).
        
        Args:
            sentences: List of sentences
        
        Returns:
            List of TF-IDF vectors
        """
        import math
        from collections import Counter
        
        # Tokenize sentences
        docs = [self._tokenize(s) for s in sentences]
        
        # Calculate document frequency
        df = Counter()
        for doc in docs:
            df.update(set(doc))
        
        # Calculate TF-IDF vectors
        vectors = []
        for doc in docs:
            tf = Counter(doc)
            vector = {}
            for word, count in tf.items():
                tf_score = count / len(doc) if doc else 0
                idf_score = math.log(len(sentences) / (df[word] + 1))
                vector[word] = tf_score * idf_score
            vectors.append(vector)
        
        return vectors
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Split by whitespace and Chinese characters
        words = re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', text.lower())
        return words
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
        
        Returns:
            Similarity score (0-1)
        """
        import math
        
        # Get common words
        common = set(vec1.keys()) & set(vec2.keys())
        
        if not common:
            return 0.0
        
        # Calculate dot product
        dot_product = sum(vec1[w] * vec2[w] for w in common)
        
        # Calculate magnitudes
        mag1 = math.sqrt(sum(v**2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v**2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
