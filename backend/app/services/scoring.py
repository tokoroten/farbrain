"""
Novelty scoring service with pluggable transformation functions.

This module provides novelty scoring based on cosine similarity between
idea embeddings, with customizable transformation functions.
"""

from typing import Callable, Protocol
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityTransform(Protocol):
    """Protocol for similarity transformation functions."""

    def __call__(self, similarities: np.ndarray) -> float:
        """
        Transform similarity array to novelty score.

        Args:
            similarities: Array of cosine similarities (0-1) between
                         new idea and existing ideas

        Returns:
            Novelty score (0-100)
        """
        ...


def linear_distance_transform(similarities: np.ndarray) -> float:
    """
    Linear transformation: average distance as score.

    Score = mean(1 - similarity) * 100

    Args:
        similarities: Cosine similarities (0-1)

    Returns:
        Novelty score (0-100)
    """
    if len(similarities) == 0:
        return 50.0  # Default score for first idea

    distances = 1 - similarities
    avg_distance = np.mean(distances)

    # Scale to 0-100 (cosine distance is in range 0-2)
    score = min(100.0, avg_distance * 50.0)
    return float(score)


def min_distance_transform(similarities: np.ndarray) -> float:
    """
    Minimum distance transformation: closest idea distance as score.

    Score = min(100, (min(1 - similarity))^1.5 * 300)
    Higher score means more different from all existing ideas.
    Uses power of 1.5 to emphasize novel ideas and penalize similar ones.

    Args:
        similarities: Cosine similarities (0-1)

    Returns:
        Novelty score (0-100)
    """
    if len(similarities) == 0:
        return 50.0

    distances = 1 - similarities
    min_distance = np.min(distances)

    # Power of 1.5 to emphasize novelty, multiply by 300, clip to [0, 100]
    score = min(100.0, (min_distance ** 1.5) * 300.0)
    return float(score)


def exponential_distance_transform(similarities: np.ndarray, beta: float = 2.0) -> float:
    """
    Exponential transformation: emphasizes larger distances.

    Score = mean((1 - similarity) ^ beta) * 100

    Args:
        similarities: Cosine similarities (0-1)
        beta: Exponential factor (>1 emphasizes outliers, <1 dampens)

    Returns:
        Novelty score (0-100)
    """
    if len(similarities) == 0:
        return 50.0

    distances = 1 - similarities
    exp_distances = np.power(distances, beta)
    avg_exp_distance = np.mean(exp_distances)

    # Scale appropriately based on beta
    score = min(100.0, avg_exp_distance * 50.0 * (2.0 / beta))
    return float(score)


def percentile_distance_transform(
    similarities: np.ndarray,
    percentile: float = 75.0
) -> float:
    """
    Percentile-based transformation: uses specific percentile of distances.

    Score = percentile(1 - similarity, p) * 100

    Args:
        similarities: Cosine similarities (0-1)
        percentile: Percentile to use (0-100)

    Returns:
        Novelty score (0-100)
    """
    if len(similarities) == 0:
        return 50.0

    distances = 1 - similarities
    percentile_distance = np.percentile(distances, percentile)

    score = min(100.0, percentile_distance * 50.0)
    return float(score)


def top_k_distance_transform(similarities: np.ndarray, k: int = 5) -> float:
    """
    Top-K transformation: average of K closest ideas.

    Score = mean(top_k(1 - similarity)) * 100

    Args:
        similarities: Cosine similarities (0-1)
        k: Number of closest ideas to consider

    Returns:
        Novelty score (0-100)
    """
    if len(similarities) == 0:
        return 50.0

    distances = 1 - similarities
    actual_k = min(k, len(distances))

    # Get k smallest distances (closest ideas)
    top_k_distances = np.partition(distances, actual_k - 1)[:actual_k]
    avg_top_k = np.mean(top_k_distances)

    score = min(100.0, avg_top_k * 50.0)
    return float(score)


class NoveltyScorer:
    """
    Novelty scorer with pluggable transformation function.

    Examples:
        >>> scorer = NoveltyScorer(linear_distance_transform)
        >>> score = scorer.calculate_score(new_embedding, existing_embeddings)

        >>> # Custom transform
        >>> def custom_transform(similarities):
        ...     return np.mean(similarities) * 100
        >>> scorer = NoveltyScorer(custom_transform)
    """

    def __init__(self, transform_fn: Callable[[np.ndarray], float] | None = None):
        """
        Initialize scorer with transformation function.

        Args:
            transform_fn: Function to transform similarities to score.
                         If None, uses linear_distance_transform.
        """
        self.transform_fn = transform_fn or linear_distance_transform

    def calculate_score(
        self,
        new_embedding: list[float] | np.ndarray,
        existing_embeddings: list[list[float]] | np.ndarray,
    ) -> float:
        """
        Calculate novelty score for new idea.

        Args:
            new_embedding: Embedding vector of new idea (384-dim)
            existing_embeddings: List of existing idea embeddings

        Returns:
            Novelty score (0-100)

        Raises:
            ValueError: If embeddings have invalid dimensions
        """
        # Convert to numpy arrays
        new_emb = np.array(new_embedding).reshape(1, -1)

        if len(existing_embeddings) == 0:
            return self.transform_fn(np.array([]))

        existing_embs = np.array(existing_embeddings)

        # Validate dimensions
        if new_emb.shape[1] != existing_embs.shape[1]:
            raise ValueError(
                f"Embedding dimension mismatch: new={new_emb.shape[1]}, "
                f"existing={existing_embs.shape[1]}"
            )

        # Calculate cosine similarities
        similarities = cosine_similarity(new_emb, existing_embs)[0]

        # Apply transformation
        score = self.transform_fn(similarities)

        return float(score)

    def set_transform(self, transform_fn: Callable[[np.ndarray], float]) -> None:
        """
        Update transformation function.

        Args:
            transform_fn: New transformation function
        """
        self.transform_fn = transform_fn


# Default scorer instance
default_scorer = NoveltyScorer(linear_distance_transform)


def calculate_novelty_score(
    new_embedding: list[float] | np.ndarray,
    existing_embeddings: list[list[float]] | np.ndarray,
    transform_fn: Callable[[np.ndarray], float] | None = None,
) -> float:
    """
    Convenience function to calculate novelty score.

    Args:
        new_embedding: Embedding vector of new idea
        existing_embeddings: List of existing idea embeddings
        transform_fn: Optional transformation function (uses default if None)

    Returns:
        Novelty score (0-100)
    """
    scorer = NoveltyScorer(transform_fn)
    return scorer.calculate_score(new_embedding, existing_embeddings)
