"""
Clustering service for idea visualization and grouping.

Provides UMAP dimensionality reduction, k-means clustering, and convex hull
computation for idea visualization.
"""

import math
import random
from typing import Any
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import ConvexHull
import umap

from backend.app.core.config import settings


@dataclass
class ClusteringResult:
    """Result of clustering operation."""

    coordinates: np.ndarray  # (n_ideas, 2) - UMAP 2D coordinates
    cluster_labels: np.ndarray  # (n_ideas,) - Cluster assignments
    n_clusters: int  # Number of clusters
    convex_hulls: dict[int, list[list[float]]]  # Cluster ID -> hull vertices


class ClusteringService:
    """
    Service for dimensionality reduction and clustering.

    Workflow:
    1. UMAP: High-dim embeddings -> 2D coordinates
    2. K-means: Group similar ideas into clusters
    3. Convex hull: Compute cluster boundaries

    Examples:
        >>> service = ClusteringService()
        >>> result = service.fit_transform(embeddings)
        >>> new_coords = service.transform(new_embedding)
    """

    def __init__(
        self,
        n_neighbors: int | None = None,
        min_dist: float | None = None,
        random_state: int = 42,
    ):
        """
        Initialize clustering service.

        Args:
            n_neighbors: UMAP n_neighbors parameter
            min_dist: UMAP min_dist parameter
            random_state: Random seed for reproducibility
        """
        self.n_neighbors = n_neighbors or settings.umap_n_neighbors
        self.min_dist = min_dist or settings.umap_min_dist
        self.random_state = random_state

        self.umap_model: umap.UMAP | None = None
        self.kmeans_model: KMeans | None = None

    def _calculate_n_clusters(self, n_ideas: int) -> int:
        """
        Calculate optimal number of clusters.

        Uses cube root formula: max(5, ceil(n_ideas^(1/3)))

        Args:
            n_ideas: Number of ideas

        Returns:
            Number of clusters (minimum 5)
        """
        if n_ideas < settings.min_ideas_for_clustering:
            return 5  # Default minimum

        n_clusters = max(5, math.ceil(n_ideas ** (1 / 3)))

        # Cap at max_clusters
        n_clusters = min(n_clusters, settings.max_clusters)

        return n_clusters

    def _generate_random_coordinates(
        self,
        n_points: int,
        x_range: tuple[float, float] = (-10, 10),
        y_range: tuple[float, float] = (-10, 10),
    ) -> np.ndarray:
        """
        Generate random 2D coordinates.

        Used for first 1-9 ideas before UMAP is available.

        Args:
            n_points: Number of points
            x_range: X coordinate range
            y_range: Y coordinate range

        Returns:
            Array of shape (n_points, 2)
        """
        np.random.seed(self.random_state)

        x_coords = np.random.uniform(x_range[0], x_range[1], n_points)
        y_coords = np.random.uniform(y_range[0], y_range[1], n_points)

        return np.column_stack([x_coords, y_coords])

    def fit_transform(
        self,
        embeddings: np.ndarray | list[list[float]],
    ) -> ClusteringResult:
        """
        Fit UMAP and k-means on embeddings, return clustering result.

        Args:
            embeddings: High-dimensional embeddings, shape (n_ideas, embedding_dim)

        Returns:
            ClusteringResult with coordinates, labels, and hulls

        Raises:
            ValueError: If embeddings array is invalid
        """
        embeddings = np.array(embeddings)

        if len(embeddings.shape) != 2:
            raise ValueError(f"Embeddings must be 2D array, got shape {embeddings.shape}")

        n_ideas = embeddings.shape[0]

        # Case 1: Less than min_ideas_for_clustering (default 10)
        if n_ideas < settings.min_ideas_for_clustering:
            coordinates = self._generate_random_coordinates(n_ideas)
            # No clustering yet, assign all to cluster 0
            cluster_labels = np.zeros(n_ideas, dtype=int)
            convex_hulls = {}

            return ClusteringResult(
                coordinates=coordinates,
                cluster_labels=cluster_labels,
                n_clusters=1,
                convex_hulls=convex_hulls,
            )

        # Case 2: Enough ideas for UMAP + k-means
        # UMAP dimensionality reduction
        self.umap_model = umap.UMAP(
            n_components=2,
            n_neighbors=min(self.n_neighbors, n_ideas - 1),
            min_dist=self.min_dist,
            metric="cosine",
            random_state=self.random_state,
        )

        coordinates = self.umap_model.fit_transform(embeddings)

        # K-means clustering
        n_clusters = self._calculate_n_clusters(n_ideas)

        self.kmeans_model = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10,
        )

        cluster_labels = self.kmeans_model.fit_predict(coordinates)

        # Compute convex hulls
        convex_hulls = self._compute_convex_hulls(coordinates, cluster_labels)

        return ClusteringResult(
            coordinates=coordinates,
            cluster_labels=cluster_labels,
            n_clusters=n_clusters,
            convex_hulls=convex_hulls,
        )

    def transform(
        self,
        embedding: np.ndarray | list[float],
    ) -> tuple[float, float]:
        """
        Transform single new embedding to 2D coordinates.

        Uses fitted UMAP model. If model not fitted, returns random coordinates.

        Args:
            embedding: Single embedding vector

        Returns:
            (x, y) coordinates

        Raises:
            ValueError: If embedding dimension doesn't match
        """
        embedding = np.array(embedding).reshape(1, -1)

        if self.umap_model is None:
            # Not fitted yet, return random coordinates
            coords = self._generate_random_coordinates(1)
            return float(coords[0, 0]), float(coords[0, 1])

        # Transform using fitted UMAP
        coords = self.umap_model.transform(embedding)

        return float(coords[0, 0]), float(coords[0, 1])

    def predict_cluster(
        self,
        coordinates: tuple[float, float] | np.ndarray,
    ) -> int:
        """
        Predict cluster label for given 2D coordinates.

        Uses fitted k-means model. If not fitted, returns 0.

        Args:
            coordinates: (x, y) coordinates

        Returns:
            Cluster label (integer)
        """
        if self.kmeans_model is None:
            return 0

        coords = np.array(coordinates).reshape(1, -1)
        cluster_label = self.kmeans_model.predict(coords)

        return int(cluster_label[0])

    def _compute_convex_hulls(
        self,
        coordinates: np.ndarray,
        cluster_labels: np.ndarray,
    ) -> dict[int, list[list[float]]]:
        """
        Compute convex hull for each cluster.

        Args:
            coordinates: 2D coordinates, shape (n_ideas, 2)
            cluster_labels: Cluster assignments, shape (n_ideas,)

        Returns:
            Dictionary mapping cluster_id to hull vertices [[x, y], ...]
        """
        hulls = {}

        unique_labels = np.unique(cluster_labels)

        for label in unique_labels:
            # Get points in this cluster
            mask = cluster_labels == label
            cluster_points = coordinates[mask]

            # Need at least 3 points for convex hull
            if len(cluster_points) < 3:
                # Use all points as hull vertices
                hulls[int(label)] = cluster_points.tolist()
                continue

            try:
                # Compute convex hull
                hull = ConvexHull(cluster_points)
                hull_vertices = cluster_points[hull.vertices].tolist()
                hulls[int(label)] = hull_vertices
            except Exception:
                # Fallback: use all points if hull computation fails
                hulls[int(label)] = cluster_points.tolist()

        return hulls

    def sample_cluster_ideas(
        self,
        cluster_id: int,
        cluster_labels: np.ndarray,
        idea_ids: list[str],
        sample_size: int | None = None,
    ) -> list[str]:
        """
        Randomly sample ideas from a specific cluster.

        Args:
            cluster_id: Target cluster ID
            cluster_labels: Array of cluster assignments
            idea_ids: List of idea IDs (same length as cluster_labels)
            sample_size: Number of ideas to sample (default from config)

        Returns:
            List of sampled idea IDs

        Raises:
            ValueError: If inputs have mismatched lengths
        """
        if len(cluster_labels) != len(idea_ids):
            raise ValueError("cluster_labels and idea_ids must have same length")

        sample_size = sample_size or settings.cluster_sample_size

        # Get ideas in this cluster
        mask = cluster_labels == cluster_id
        cluster_idea_ids = [
            idea_id for idea_id, in_cluster in zip(idea_ids, mask) if in_cluster
        ]

        # Sample or use all if fewer than sample_size
        if len(cluster_idea_ids) <= sample_size:
            return cluster_idea_ids

        return random.sample(cluster_idea_ids, sample_size)


# Global service instance
_clustering_service: ClusteringService | None = None


def get_clustering_service() -> ClusteringService:
    """
    Get singleton clustering service instance.

    Returns:
        Cached ClusteringService instance
    """
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service


def cluster_ideas(embeddings: list[list[float]]) -> ClusteringResult:
    """
    Convenience function to cluster ideas.

    Args:
        embeddings: List of embedding vectors

    Returns:
        ClusteringResult
    """
    service = get_clustering_service()
    return service.fit_transform(embeddings)


def transform_idea(embedding: list[float]) -> tuple[float, float]:
    """
    Convenience function to transform single idea.

    Args:
        embedding: Embedding vector

    Returns:
        (x, y) coordinates
    """
    service = get_clustering_service()
    return service.transform(embedding)
