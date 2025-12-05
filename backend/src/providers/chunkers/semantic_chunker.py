"""Semantic-based chunker implementation with TF-IDF similarity."""
from typing import List, Dict, Any
import re
from .base_chunker import BaseChunker


class SemanticChunker(BaseChunker):
    """Chunker that splits text by semantic similarity using TF-IDF."""
    
    def validate_params(self) -> None:
        """
        Validate semantic chunking parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        threshold = self.params.get('similarity_threshold', 0.7)
        min_size = self.params.get('min_chunk_size', 200)
        
        if not isinstance(threshold, (int, float)) or threshold < 0.3 or threshold > 0.9:
            raise ValueError("similarity_threshold must be between 0.3 and 0.9")
        
        if not isinstance(min_size, int) or min_size <= 0:
            raise ValueError("min_chunk_size must be a positive integer")
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text by semantic similarity.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata about the source document
        
        Returns:
            List of chunk dictionaries
        """
        threshold = self.params.get('similarity_threshold', 0.7)
        min_size = self.params.get('min_chunk_size', 200)
        
        if not text or len(text) == 0:
            return []
        
        # Try semantic chunking, fallback if it fails
        try:
            return self._semantic_chunk(text, threshold, min_size)
        except Exception:
            # Fallback to sentence-based chunking
            return self._fallback_to_sentences(text, min_size)
    
    def _semantic_chunk(
        self,
        text: str,
        threshold: float,
        min_size: int
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic chunking using TF-IDF similarity.
        
        Args:
            text: Input text
            threshold: Similarity threshold
            min_size: Minimum chunk size
        
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
            
            # Decide whether to continue current chunk or start new one
            if similarity >= threshold and current_length < 2000:
                # Continue current chunk
                current_chunk_sentences.append(sentences[i])
            else:
                # Start new chunk if current meets min size
                if current_length >= min_size:
                    content = ' '.join(current_chunk_sentences)
                    chunk = self._create_chunk(
                        content=content,
                        index=chunk_index,
                        start_pos=text.find(current_chunk_sentences[0], current_start),
                        end_pos=text.find(current_chunk_sentences[-1], current_start) + len(current_chunk_sentences[-1]),
                        strategy="semantic",
                        sentence_count=len(current_chunk_sentences),
                        avg_similarity=threshold
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_start = text.find(sentences[i], current_start)
                
                current_chunk_sentences = [sentences[i]]
        
        # Add final chunk
        if current_chunk_sentences:
            current_length = sum(len(s) for s in current_chunk_sentences)
            if current_length >= min_size or not chunks:
                content = ' '.join(current_chunk_sentences)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=text.find(current_chunk_sentences[0], current_start),
                    end_pos=len(text),
                    strategy="semantic",
                    sentence_count=len(current_chunk_sentences),
                    avg_similarity=threshold
                )
                chunks.append(chunk)
        
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
                # Save current chunk
                content = ' '.join(current_chunk)
                chunk = self._create_chunk(
                    content=content,
                    index=chunk_index,
                    start_pos=current_start,
                    end_pos=current_start + len(content),
                    strategy="semantic",
                    sentence_count=len(current_chunk),
                    fallback_strategy="sentence",
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
                sentence_count=len(current_chunk),
                fallback_strategy="sentence",
                fallback_reason="semantic_analysis_failed"
            )
            chunks.append(chunk)
        
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
