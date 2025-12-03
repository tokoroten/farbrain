"""
Embedding service using Sentence Transformers.

Provides text-to-vector embedding functionality with caching and
async support for optimal performance.
"""

from typing import Any
import numpy as np
from functools import lru_cache
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from sentence_transformers import SentenceTransformer

from backend.app.core.config import settings


class EmbeddingService:
    """
    Service for generating text embeddings using Sentence Transformers.

    This service provides:
    - Lazy model loading
    - Thread-safe embedding generation
    - Async wrapper for non-blocking operations
    - Configurable model selection via environment

    Examples:
        >>> service = EmbeddingService()
        >>> embedding = await service.embed("Hello world")
        >>> len(embedding)
        768
    """

    def __init__(self, model_name: str | None = None):
        """
        Initialize embedding service.

        Args:
            model_name: Sentence Transformers model name.
                       If None, uses setting from config.
        """
        self.model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._model_lock = threading.Lock()  # Thread lock for lazy model loading
        self._executor = ThreadPoolExecutor(max_workers=2)

    @property
    def model(self) -> SentenceTransformer:
        """
        Lazy load Sentence Transformers model (thread-safe).

        Returns:
            Loaded SentenceTransformer model

        Note:
            Model is loaded on first access and cached.
            First load may take time to download model.
            Uses thread lock to prevent concurrent loading.
        """
        if self._model is None:
            with self._model_lock:
                # Double-check after acquiring lock
                if self._model is None:
                    self._model = SentenceTransformer(self.model_name)
                    # Move to GPU if available
                    if hasattr(self._model, 'to'):
                        try:
                            import torch
                            if torch.cuda.is_available():
                                self._model = self._model.to('cuda')
                        except ImportError:
                            pass
        return self._model

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding.

        - Strips leading/trailing whitespace
        - Removes newlines and replaces with spaces
        - Normalizes multiple spaces to single space

        Args:
            text: Raw text input

        Returns:
            Preprocessed text
        """
        # Remove newlines and replace with space
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Normalize multiple spaces to single space
        text = ' '.join(text.split())
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def embed_sync(
        self,
        text: str | list[str],
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings synchronously.

        Args:
            text: Single text or list of texts to embed
            normalize: Whether to L2-normalize embeddings

        Returns:
            Embedding array. Shape:
            - (embedding_dim,) for single text
            - (n_texts, embedding_dim) for multiple texts

        Raises:
            ValueError: If text is empty
        """
        # Preprocess text(s)
        if isinstance(text, str):
            text = self._preprocess_text(text)
            if not text:
                raise ValueError("Text cannot be empty")
        elif isinstance(text, list):
            text = [self._preprocess_text(t) for t in text]
            if not text or all(not t for t in text):
                raise ValueError("Text list cannot be empty")

        embeddings = self.model.encode(
            text,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embeddings

    async def embed(
        self,
        text: str | list[str],
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings asynchronously.

        Args:
            text: Single text or list of texts to embed
            normalize: Whether to L2-normalize embeddings

        Returns:
            Embedding array

        Note:
            Runs in thread pool to avoid blocking event loop.
        """
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self._executor,
            self.embed_sync,
            text,
            normalize,
        )
        return embeddings

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> list[np.ndarray]:
        """
        Generate embeddings for large batches efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            normalize: Whether to L2-normalize embeddings

        Returns:
            List of embedding arrays

        Note:
            Automatically batches large inputs for efficiency.
        """
        if not texts:
            return []

        # Process in batches
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = await self.embed(batch, normalize=normalize)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def get_embedding_dimension(self) -> int:
        """
        Get embedding dimension for current model.

        Returns:
            Embedding vector dimension
        """
        return self.model.get_sentence_embedding_dimension()

    def __del__(self):
        """Cleanup executor on deletion."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)


# Global singleton instance
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Get singleton embedding service instance.

    Returns:
        Cached EmbeddingService instance

    Note:
        Service is cached for reuse across requests.
    """
    return EmbeddingService()


async def embed_text(text: str, normalize: bool = True) -> list[float]:
    """
    Convenience function to embed single text.

    Args:
        text: Text to embed
        normalize: Whether to normalize embedding

    Returns:
        Embedding as list of floats

    Examples:
        >>> embedding = await embed_text("Hello world")
        >>> len(embedding)
        768
    """
    service = get_embedding_service()
    embedding = await service.embed(text, normalize=normalize)
    return embedding.tolist()


async def embed_texts(texts: list[str], normalize: bool = True) -> list[list[float]]:
    """
    Convenience function to embed multiple texts.

    Args:
        texts: List of texts to embed
        normalize: Whether to normalize embeddings

    Returns:
        List of embeddings as lists of floats
    """
    service = get_embedding_service()
    embeddings = await service.embed(texts, normalize=normalize)
    return embeddings.tolist()
