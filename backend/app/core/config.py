"""Application configuration."""

from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI Settings (for concurrent multi-user LLM requests)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")

    # Embedding Model (Sentence Transformers)
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        description="Sentence Transformers model name (768-dim, multilingual, high accuracy)"
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension (depends on model)"
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./farbrain.db",
        description="Database connection URL"
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Security
    secret_key: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        description="Secret key for JWT token generation"
    )
    admin_password: str = Field(
        default="admin",
        description="Admin password for management endpoints"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=12, description="JWT token expiration in hours")

    # Clustering Parameters
    min_ideas_for_clustering: int = Field(
        default=10,
        description="Minimum number of ideas before clustering starts"
    )
    clustering_interval: int = Field(
        default=10,
        description="Full re-clustering (UMAP + k-means + LLM labels) every N ideas"
    )
    reclustering_interval: int = Field(
        default=10,
        description="Full re-clustering interval (same as clustering_interval for consistency)"
    )
    max_clusters: int = Field(
        default=20,
        description="Maximum number of clusters"
    )
    cluster_sample_size: int = Field(
        default=10,
        description="Number of ideas to sample for cluster summarization"
    )

    # UMAP Parameters
    umap_n_neighbors: int = Field(default=50, description="UMAP n_neighbors parameter (larger = global structure)")
    umap_min_dist: float = Field(default=0.3, description="UMAP min_dist parameter (larger = more spread out)")

    # Scoring Parameters
    anomaly_contamination: float = Field(
        default=0.1,
        description="Isolation Forest contamination parameter"
    )

    # Session Parameters
    default_session_duration: int = Field(
        default=7200,
        description="Default session duration in seconds (2 hours)"
    )

    # Development Settings
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Idea Validation
    max_idea_length: int = Field(
        default=2000,
        description="Maximum length of idea text"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Validate embedding dimension is positive."""
        if v <= 0:
            raise ValueError("embedding_dimension must be positive")
        return v

    @field_validator("min_ideas_for_clustering", "clustering_interval", "reclustering_interval")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate integer is positive."""
        if v <= 0:
            raise ValueError(f"Value must be positive, got {v}")
        return v

    @field_validator("max_clusters")
    @classmethod
    def validate_max_clusters(cls, v: int) -> int:
        """Validate max_clusters is within reasonable range."""
        if v < 2:
            raise ValueError("max_clusters must be at least 2")
        if v > 100:
            raise ValueError("max_clusters should not exceed 100 for performance")
        return v

    @field_validator("anomaly_contamination")
    @classmethod
    def validate_contamination(cls, v: float) -> float:
        """Validate contamination is between 0 and 1."""
        if not 0 < v < 1:
            raise ValueError("anomaly_contamination must be between 0 and 1")
        return v

    @field_validator("umap_min_dist")
    @classmethod
    def validate_umap_min_dist(cls, v: float) -> float:
        """Validate UMAP min_dist is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("umap_min_dist must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def validate_clustering_intervals(self) -> "Settings":
        """Validate clustering intervals are logically consistent."""
        if self.clustering_interval > self.reclustering_interval:
            raise ValueError(
                "clustering_interval must be less than or equal to reclustering_interval"
            )
        if self.min_ideas_for_clustering > self.clustering_interval:
            raise ValueError(
                "min_ideas_for_clustering should be less than or equal to clustering_interval"
            )
        return self


# Global settings instance
settings = Settings()
