"""Unit tests for ClusteringService."""

import pytest
import numpy as np
from backend.app.services.clustering import (
    ClusteringService,
    ClusteringResult,
    get_clustering_service,
    cluster_ideas,
    transform_idea,
)


class TestClusteringService:
    """Test cases for ClusteringService class."""

    def test_initialization(self):
        """Test ClusteringService initialization."""
        service = ClusteringService(n_neighbors=10, min_dist=0.2, random_state=123)

        assert service.n_neighbors == 10
        assert service.min_dist == 0.2
        assert service.random_state == 123
        assert service.umap_model is None
        assert service.kmeans_model is None

    def test_initialization_with_defaults(self):
        """Test ClusteringService initialization with default parameters."""
        service = ClusteringService()

        # Should use settings defaults
        assert service.n_neighbors is not None
        assert service.min_dist is not None
        assert service.random_state == 42

    def test_calculate_n_clusters_small(self):
        """Test cluster count calculation for small datasets."""
        service = ClusteringService()

        # Less than min_ideas_for_clustering (10)
        assert service._calculate_n_clusters(5) == 5
        assert service._calculate_n_clusters(9) == 5

    def test_calculate_n_clusters_medium(self):
        """Test cluster count calculation for medium datasets."""
        service = ClusteringService()

        # 10-100 ideas
        # Formula: max(5, ceil(n_ideas^(1/3)))
        assert service._calculate_n_clusters(10) >= 5
        assert service._calculate_n_clusters(27) == 5  # 27^(1/3) = 3, but min is 5
        assert service._calculate_n_clusters(125) == 5  # 125^(1/3) = 5
        assert service._calculate_n_clusters(216) == 6  # 216^(1/3) = 6

    def test_calculate_n_clusters_large(self):
        """Test cluster count calculation for large datasets."""
        service = ClusteringService()

        # 1000 ideas: 1000^(1/3) = 10
        assert service._calculate_n_clusters(1000) == 10

    def test_calculate_n_clusters_max_cap(self):
        """Test cluster count caps at max_clusters."""
        service = ClusteringService()

        # Very large dataset should be capped
        # 10000^(1/3) = 21.5, but should be capped at settings.max_clusters (default 20)
        n_clusters = service._calculate_n_clusters(10000)
        assert n_clusters <= 20  # max_clusters from settings

    def test_generate_random_coordinates(self):
        """Test random coordinate generation."""
        service = ClusteringService(random_state=42)

        coords = service._generate_random_coordinates(5)

        assert coords.shape == (5, 2)
        # Check coordinates are within range
        assert np.all(coords[:, 0] >= -10) and np.all(coords[:, 0] <= 10)
        assert np.all(coords[:, 1] >= -10) and np.all(coords[:, 1] <= 10)

    def test_generate_random_coordinates_custom_range(self):
        """Test random coordinate generation with custom range."""
        service = ClusteringService(random_state=42)

        coords = service._generate_random_coordinates(
            3, x_range=(0, 100), y_range=(-50, 50)
        )

        assert coords.shape == (3, 2)
        assert np.all(coords[:, 0] >= 0) and np.all(coords[:, 0] <= 100)
        assert np.all(coords[:, 1] >= -50) and np.all(coords[:, 1] <= 50)

    def test_generate_random_coordinates_reproducible(self):
        """Test random coordinate generation is reproducible."""
        service1 = ClusteringService(random_state=42)
        service2 = ClusteringService(random_state=42)

        coords1 = service1._generate_random_coordinates(5)
        coords2 = service2._generate_random_coordinates(5)

        np.testing.assert_array_almost_equal(coords1, coords2)

    def test_fit_transform_small_dataset(self):
        """Test fit_transform with less than 10 ideas (random placement)."""
        service = ClusteringService(random_state=42)

        # Create 5 random embeddings
        embeddings = np.random.rand(5, 128)

        result = service.fit_transform(embeddings)

        assert isinstance(result, ClusteringResult)
        assert result.coordinates.shape == (5, 2)
        assert result.cluster_labels.shape == (5,)
        assert result.n_clusters == 1
        assert np.all(result.cluster_labels == 0)  # All in cluster 0
        assert len(result.convex_hulls) == 0  # No hulls for small datasets

        # Models should not be fitted
        assert service.umap_model is None
        assert service.kmeans_model is None

    def test_fit_transform_large_dataset(self):
        """Test fit_transform with 50 ideas (UMAP + k-means)."""
        service = ClusteringService(random_state=42)

        # Create 50 random embeddings
        embeddings = np.random.rand(50, 128)

        result = service.fit_transform(embeddings)

        assert isinstance(result, ClusteringResult)
        assert result.coordinates.shape == (50, 2)
        assert result.cluster_labels.shape == (50,)
        assert result.n_clusters >= 5  # At least 5 clusters
        assert len(result.convex_hulls) > 0

        # Models should be fitted
        assert service.umap_model is not None
        assert service.kmeans_model is not None

    def test_fit_transform_invalid_shape(self):
        """Test fit_transform with invalid embedding shape."""
        service = ClusteringService()

        # 1D array instead of 2D
        embeddings = np.random.rand(10)

        with pytest.raises(ValueError, match="must be 2D array"):
            service.fit_transform(embeddings)

    def test_fit_transform_list_input(self):
        """Test fit_transform accepts list of lists."""
        service = ClusteringService(random_state=42)

        # List of lists
        embeddings = [[0.1, 0.2, 0.3] for _ in range(5)]

        result = service.fit_transform(embeddings)

        assert isinstance(result, ClusteringResult)
        assert result.coordinates.shape == (5, 2)

    def test_transform_without_fitted_model(self):
        """Test transform returns random coordinates when model not fitted."""
        service = ClusteringService(random_state=42)

        embedding = np.random.rand(128)
        x, y = service.transform(embedding)

        assert isinstance(x, float)
        assert isinstance(y, float)

    def test_transform_with_fitted_model(self):
        """Test transform uses UMAP model after fitting."""
        service = ClusteringService(random_state=42)

        # Fit on dataset
        embeddings = np.random.rand(20, 128)
        service.fit_transform(embeddings)

        # Transform new embedding
        new_embedding = np.random.rand(128)
        x, y = service.transform(new_embedding)

        assert isinstance(x, float)
        assert isinstance(y, float)

    def test_transform_list_input(self):
        """Test transform accepts list input."""
        service = ClusteringService(random_state=42)

        # Fit on dataset
        embeddings = np.random.rand(20, 128)
        service.fit_transform(embeddings)

        # Transform with list
        new_embedding = [0.1] * 128
        x, y = service.transform(new_embedding)

        assert isinstance(x, float)
        assert isinstance(y, float)

    def test_predict_cluster_without_fitted_model(self):
        """Test predict_cluster returns 0 when model not fitted."""
        service = ClusteringService()

        cluster = service.predict_cluster((1.0, 2.0))

        assert cluster == 0

    def test_predict_cluster_with_fitted_model(self):
        """Test predict_cluster uses k-means model after fitting."""
        service = ClusteringService(random_state=42)

        # Fit on dataset
        embeddings = np.random.rand(50, 128)
        result = service.fit_transform(embeddings)

        # Predict cluster for a coordinate
        cluster = service.predict_cluster((result.coordinates[0, 0], result.coordinates[0, 1]))

        assert isinstance(cluster, int)
        assert 0 <= cluster < result.n_clusters

    def test_predict_cluster_numpy_input(self):
        """Test predict_cluster accepts numpy array."""
        service = ClusteringService(random_state=42)

        # Fit on dataset
        embeddings = np.random.rand(50, 128)
        service.fit_transform(embeddings)

        # Predict with numpy array
        coords = np.array([1.0, 2.0])
        cluster = service.predict_cluster(coords)

        assert isinstance(cluster, int)

    def test_compute_convex_hulls(self):
        """Test convex hull computation."""
        service = ClusteringService()

        # Create coordinates for 2 clusters
        coords = np.array([
            [0, 0], [1, 0], [0, 1],  # Cluster 0 (triangle)
            [5, 5], [6, 5], [5, 6],  # Cluster 1 (triangle)
        ])
        labels = np.array([0, 0, 0, 1, 1, 1])

        hulls = service._compute_convex_hulls(coords, labels)

        assert len(hulls) == 2
        assert 0 in hulls
        assert 1 in hulls
        assert len(hulls[0]) == 3  # Triangle has 3 vertices
        assert len(hulls[1]) == 3

    def test_compute_convex_hulls_small_cluster(self):
        """Test convex hull with less than 3 points."""
        service = ClusteringService()

        # Cluster with only 2 points
        coords = np.array([[0, 0], [1, 1]])
        labels = np.array([0, 0])

        hulls = service._compute_convex_hulls(coords, labels)

        assert len(hulls) == 1
        assert len(hulls[0]) == 2  # All points are used as hull

    def test_sample_cluster_ideas(self):
        """Test sampling ideas from cluster."""
        service = ClusteringService()

        cluster_labels = np.array([0, 0, 0, 1, 1, 1])
        idea_ids = ["id1", "id2", "id3", "id4", "id5", "id6"]

        # Sample from cluster 0
        sampled = service.sample_cluster_ideas(0, cluster_labels, idea_ids, sample_size=2)

        assert len(sampled) == 2
        assert all(id in ["id1", "id2", "id3"] for id in sampled)

    def test_sample_cluster_ideas_all(self):
        """Test sampling when cluster has fewer ideas than sample size."""
        service = ClusteringService()

        cluster_labels = np.array([0, 0, 1, 1, 1])
        idea_ids = ["id1", "id2", "id3", "id4", "id5"]

        # Cluster 0 has 2 ideas, request 5
        sampled = service.sample_cluster_ideas(0, cluster_labels, idea_ids, sample_size=5)

        assert len(sampled) == 2  # Returns all 2 ideas
        assert set(sampled) == {"id1", "id2"}

    def test_sample_cluster_ideas_mismatched_length(self):
        """Test sampling with mismatched input lengths."""
        service = ClusteringService()

        cluster_labels = np.array([0, 0, 0])
        idea_ids = ["id1", "id2"]  # Different length

        with pytest.raises(ValueError, match="must have same length"):
            service.sample_cluster_ideas(0, cluster_labels, idea_ids)


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_get_clustering_service_singleton(self):
        """Test get_clustering_service returns singleton."""
        service1 = get_clustering_service()
        service2 = get_clustering_service()

        assert service1 is service2

    def test_cluster_ideas(self):
        """Test cluster_ideas convenience function."""
        embeddings = [[0.1, 0.2, 0.3] for _ in range(5)]

        result = cluster_ideas(embeddings)

        assert isinstance(result, ClusteringResult)

    def test_transform_idea(self):
        """Test transform_idea convenience function."""
        embedding = [0.1] * 128

        x, y = transform_idea(embedding)

        assert isinstance(x, float)
        assert isinstance(y, float)


class TestClusteringResult:
    """Test cases for ClusteringResult dataclass."""

    def test_clustering_result_creation(self):
        """Test ClusteringResult can be created."""
        result = ClusteringResult(
            coordinates=np.array([[1, 2], [3, 4]]),
            cluster_labels=np.array([0, 1]),
            n_clusters=2,
            convex_hulls={0: [[1, 2]], 1: [[3, 4]]},
        )

        assert result.coordinates.shape == (2, 2)
        assert result.cluster_labels.shape == (2,)
        assert result.n_clusters == 2
        assert len(result.convex_hulls) == 2
