"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import sessions, users, ideas, visualization, websocket, auth, dialogue, debug, reports
from backend.app.core.config import settings
from backend.app.core.exception_handlers import register_exception_handlers
from backend.app.db.base import engine, Base
# Import all models to register them with SQLAlchemy
from backend.app.models.session import Session as SessionModel
from backend.app.models.user import User as UserModel
from backend.app.models.idea import Idea as IdeaModel
from backend.app.models.cluster import Cluster as ClusterModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-load embedding model to improve first request performance
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[STARTUP] Pre-loading embedding model...")

    try:
        from backend.app.services.embedding import EmbeddingService
        embedding_service = EmbeddingService()
        # Warm up the model with a dummy embedding
        await embedding_service.embed("テスト")
        logger.info("[STARTUP] Embedding model pre-loaded successfully")
    except Exception as e:
        logger.warning(f"[STARTUP] Failed to pre-load embedding model: {e}")

    yield

    # Shutdown: Close database connections
    await engine.dispose()
    logger.info("[SHUTDOWN] Cleaned up resources")


app = FastAPI(
    title="FarBrain API",
    description="LLM-powered gamified brainstorming tool",
    version="1.0.0",
    lifespan=lifespan,
)

# Register custom exception handlers
register_exception_handlers(app)

# CORS middleware for frontend
print("=" * 80)
print(f"[CORS DEBUG] CORS_ORIGINS from env: {settings.cors_origins}")
print(f"[CORS DEBUG] Parsed origins list: {settings.cors_origins_list}")
print("=" * 80)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Load from .env file
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.include_router(visualization.router, prefix="/api")
app.include_router(dialogue.router)
app.include_router(websocket.router)
app.include_router(debug.router, prefix="/api")  # Debug endpoints
app.include_router(reports.router, prefix="/api")  # Report endpoints


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "FarBrain API",
        "version": "1.0.0",
        "description": "LLM-powered gamified brainstorming tool",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
