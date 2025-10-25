"""Application configuration."""

from typing import Literal
from pydantic import Field
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
        default="http://localhost:5173,http://localhost:3000",
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
        description="Recalculate clustering every N ideas"
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
    umap_n_neighbors: int = Field(default=15, description="UMAP n_neighbors parameter")
    umap_min_dist: float = Field(default=0.1, description="UMAP min_dist parameter")

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


# Global settings instance
settings = Settings()
