"""Unit tests for configuration validation."""

import pytest
from pydantic import ValidationError
from backend.app.core.config import Settings


class TestSettingsValidation:
    """Test cases for Settings validation."""

    def test_default_settings(self):
        """Test that default settings are valid."""
        settings = Settings()

        assert settings.log_level == "INFO"
        assert settings.embedding_dimension > 0
        assert settings.min_ideas_for_clustering > 0
        assert settings.max_clusters >= 2

    def test_log_level_validation_valid(self):
        """Test log level accepts valid values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = Settings(log_level=level)
            assert settings.log_level == level.upper()

    def test_log_level_validation_case_insensitive(self):
        """Test log level is case-insensitive."""
        settings = Settings(log_level="info")
        assert settings.log_level == "INFO"

        settings = Settings(log_level="DeBuG")
        assert settings.log_level == "DEBUG"

    def test_log_level_validation_invalid(self):
        """Test log level rejects invalid values."""
        with pytest.raises(ValidationError, match="log_level must be one of"):
            Settings(log_level="INVALID")

    def test_embedding_dimension_positive(self):
        """Test embedding dimension must be positive."""
        with pytest.raises(ValidationError, match="embedding_dimension must be positive"):
            Settings(embedding_dimension=0)

        with pytest.raises(ValidationError, match="embedding_dimension must be positive"):
            Settings(embedding_dimension=-1)

    def test_embedding_dimension_valid(self):
        """Test embedding dimension accepts positive values."""
        settings = Settings(embedding_dimension=768)
        assert settings.embedding_dimension == 768

    def test_min_ideas_for_clustering_positive(self):
        """Test min_ideas_for_clustering must be positive."""
        with pytest.raises(ValidationError, match="Value must be positive"):
            Settings(min_ideas_for_clustering=0)

        with pytest.raises(ValidationError, match="Value must be positive"):
            Settings(min_ideas_for_clustering=-5)

    def test_clustering_interval_positive(self):
        """Test clustering_interval must be positive."""
        with pytest.raises(ValidationError, match="Value must be positive"):
            Settings(clustering_interval=0)

    def test_reclustering_interval_positive(self):
        """Test reclustering_interval must be positive."""
        with pytest.raises(ValidationError, match="Value must be positive"):
            Settings(reclustering_interval=0)

    def test_max_clusters_minimum(self):
        """Test max_clusters must be at least 2."""
        with pytest.raises(ValidationError, match="max_clusters must be at least 2"):
            Settings(max_clusters=1)

    def test_max_clusters_maximum(self):
        """Test max_clusters should not exceed 100."""
        with pytest.raises(ValidationError, match="max_clusters should not exceed 100"):
            Settings(max_clusters=101)

    def test_max_clusters_valid_range(self):
        """Test max_clusters accepts valid range."""
        settings = Settings(max_clusters=20)
        assert settings.max_clusters == 20

        settings = Settings(max_clusters=2)
        assert settings.max_clusters == 2

        settings = Settings(max_clusters=100)
        assert settings.max_clusters == 100

    def test_anomaly_contamination_range(self):
        """Test anomaly_contamination must be between 0 and 1."""
        with pytest.raises(ValidationError, match="anomaly_contamination must be between 0 and 1"):
            Settings(anomaly_contamination=0.0)

        with pytest.raises(ValidationError, match="anomaly_contamination must be between 0 and 1"):
            Settings(anomaly_contamination=1.0)

        with pytest.raises(ValidationError, match="anomaly_contamination must be between 0 and 1"):
            Settings(anomaly_contamination=-0.1)

        with pytest.raises(ValidationError, match="anomaly_contamination must be between 0 and 1"):
            Settings(anomaly_contamination=1.1)

    def test_anomaly_contamination_valid_range(self):
        """Test anomaly_contamination accepts valid range."""
        settings = Settings(anomaly_contamination=0.1)
        assert settings.anomaly_contamination == 0.1

        settings = Settings(anomaly_contamination=0.5)
        assert settings.anomaly_contamination == 0.5

    def test_umap_min_dist_range(self):
        """Test umap_min_dist must be between 0 and 1."""
        with pytest.raises(ValidationError, match="umap_min_dist must be between 0 and 1"):
            Settings(umap_min_dist=-0.1)

        with pytest.raises(ValidationError, match="umap_min_dist must be between 0 and 1"):
            Settings(umap_min_dist=1.1)

    def test_umap_min_dist_valid_range(self):
        """Test umap_min_dist accepts valid range."""
        settings = Settings(umap_min_dist=0.0)
        assert settings.umap_min_dist == 0.0

        settings = Settings(umap_min_dist=0.5)
        assert settings.umap_min_dist == 0.5

        settings = Settings(umap_min_dist=1.0)
        assert settings.umap_min_dist == 1.0

    def test_clustering_intervals_logical_consistency(self):
        """Test clustering_interval must be less than reclustering_interval."""
        with pytest.raises(ValidationError, match="clustering_interval must be less than reclustering_interval"):
            Settings(clustering_interval=50, reclustering_interval=50)

        with pytest.raises(ValidationError, match="clustering_interval must be less than reclustering_interval"):
            Settings(clustering_interval=60, reclustering_interval=50)

    def test_clustering_intervals_valid(self):
        """Test valid clustering interval configuration."""
        settings = Settings(clustering_interval=10, reclustering_interval=50)
        assert settings.clustering_interval == 10
        assert settings.reclustering_interval == 50

    def test_min_ideas_clustering_interval_consistency(self):
        """Test min_ideas_for_clustering should not exceed clustering_interval."""
        with pytest.raises(ValidationError, match="min_ideas_for_clustering should be less than or equal to clustering_interval"):
            Settings(min_ideas_for_clustering=20, clustering_interval=10, reclustering_interval=50)

    def test_min_ideas_clustering_interval_valid(self):
        """Test valid min_ideas and clustering_interval configuration."""
        settings = Settings(min_ideas_for_clustering=5, clustering_interval=10, reclustering_interval=50)
        assert settings.min_ideas_for_clustering == 5
        assert settings.clustering_interval == 10

    def test_cors_origins_list_property(self):
        """Test CORS origins list property parses correctly."""
        settings = Settings(cors_origins="http://localhost:3000,http://localhost:5173")

        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_cors_origins_list_with_spaces(self):
        """Test CORS origins list handles spaces correctly."""
        settings = Settings(cors_origins="http://localhost:3000 , http://localhost:5173 ")

        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
        # Verify no trailing spaces
        assert all(not origin.startswith(" ") and not origin.endswith(" ") for origin in origins)
