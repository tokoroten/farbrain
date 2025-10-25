"""Idea management API endpoints."""

import asyncio
import math
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.base import get_db
from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.schemas.idea import IdeaCreate, IdeaListResponse, IdeaResponse
from backend.app.services.clustering import ClusteringService
from backend.app.services.embedding import EmbeddingService
from backend.app.services.llm import LLMService
from backend.app.services.scoring import NoveltyScorer
from backend.app.websocket.manager import manager

router = APIRouter(prefix="/ideas", tags=["ideas"])

# Service singletons
embedding_service = EmbeddingService()
llm_service = LLMService()
clustering_service = ClusteringService()
novelty_scorer = NoveltyScorer()


@router.post("/", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_idea(
    idea_data: IdeaCreate,
    db: AsyncSession = Depends(get_db),
) -> IdeaResponse:
    """
    Create a new idea with full ML pipeline:
    1. Verify session and user
    2. Format idea with LLM
    3. Generate embedding
    4. Calculate novelty score
    5. Assign coordinates (random for <10 ideas, UMAP for 10+)
    6. Trigger clustering if needed (every 10 ideas)
    7. Update user score
    """
    # Verify session
    session_result = await db.execute(
        select(Session).where(Session.id == idea_data.session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if not session.accepting_ideas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not accepting new ideas"
        )

    if session.status == "ended":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has ended"
        )

    # Verify user
    user_result = await db.execute(
        select(User).where(
            User.session_id == idea_data.session_id,
            User.user_id == idea_data.user_id
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this session"
        )

    # Get existing ideas for scoring and clustering
    existing_ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == idea_data.session_id)
    )
    existing_ideas = existing_ideas_result.scalars().all()
    n_existing = len(existing_ideas)

    # Step 1: Format idea with LLM
    formatted_text = await llm_service.format_idea(
        idea_data.raw_text,
        custom_prompt=session.formatting_prompt
    )

    # Step 2: Generate embedding
    embedding = await embedding_service.embed(formatted_text)
    embedding_list = embedding.tolist()

    # Step 3: Calculate novelty score
    if n_existing == 0:
        novelty_score = 100.0  # First idea gets max score
    else:
        existing_embeddings = np.array([idea.embedding for idea in existing_ideas])
        novelty_score = novelty_scorer.calculate_score(
            embedding.reshape(1, -1),
            existing_embeddings
        )

    # Step 4: Assign coordinates
    if n_existing < settings.min_ideas_for_clustering - 1:
        # Random coordinates for first 9 ideas
        x = float(np.random.uniform(-10, 10))
        y = float(np.random.uniform(-10, 10))
        cluster_id = None
    else:
        # Use UMAP for 10+ ideas
        all_embeddings = np.vstack([existing_embeddings, embedding.reshape(1, -1)])
        clustering_result = clustering_service.fit_transform(all_embeddings)

        # Get coordinates for new idea (last one)
        x = float(clustering_result.coordinates[-1, 0])
        y = float(clustering_result.coordinates[-1, 1])
        cluster_id = int(clustering_result.cluster_labels[-1])

        # Update coordinates for all existing ideas
        for i, idea in enumerate(existing_ideas):
            idea.x = float(clustering_result.coordinates[i, 0])
            idea.y = float(clustering_result.coordinates[i, 1])
            idea.cluster_id = int(clustering_result.cluster_labels[i])

    # Create idea
    idea = Idea(
        session_id=idea_data.session_id,
        user_id=idea_data.user_id,
        raw_text=idea_data.raw_text,
        formatted_text=formatted_text,
        embedding=embedding_list,
        x=x,
        y=y,
        cluster_id=cluster_id,
        novelty_score=novelty_score,
    )

    db.add(idea)

    # Update user score and count
    user.total_score += novelty_score
    user.idea_count += 1

    await db.commit()
    await db.refresh(idea)
    await db.refresh(user)

    # Step 5: Broadcast new idea via WebSocket
    await manager.send_idea_created(
        session_id=idea_data.session_id,
        idea_id=idea.id,
        user_id=idea.user_id,
        user_name=user.name,
        formatted_text=idea.formatted_text,
        raw_text=idea.raw_text,
        x=idea.x,
        y=idea.y,
        cluster_id=idea.cluster_id,
        novelty_score=idea.novelty_score,
    )

    # Step 6: Trigger clustering and labeling if needed (every 10 ideas)
    new_total = n_existing + 1
    if new_total >= settings.min_ideas_for_clustering and new_total % settings.clustering_interval == 0:
        # Run clustering and labeling in background
        asyncio.create_task(
            update_cluster_labels(idea_data.session_id, db)
        )

    return IdeaResponse(
        id=idea.id,
        session_id=idea.session_id,
        user_id=idea.user_id,
        user_name=user.name,
        raw_text=idea.raw_text,
        formatted_text=idea.formatted_text,
        x=idea.x,
        y=idea.y,
        cluster_id=idea.cluster_id,
        novelty_score=idea.novelty_score,
        timestamp=idea.created_at,
    )


async def update_cluster_labels(session_id: UUID, db: AsyncSession) -> None:
    """Background task to update cluster labels using LLM."""
    try:
        # Get session for custom prompts
        session_result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            return

        # Get all ideas
        ideas_result = await db.execute(
            select(Idea).where(Idea.session_id == session_id)
        )
        ideas = ideas_result.scalars().all()

        if not ideas:
            return

        # Group ideas by cluster
        cluster_ideas: dict[int, list[Idea]] = {}
        for idea in ideas:
            if idea.cluster_id is not None:
                if idea.cluster_id not in cluster_ideas:
                    cluster_ideas[idea.cluster_id] = []
                cluster_ideas[idea.cluster_id].append(idea)

        # Generate labels for each cluster
        for cluster_id, cluster_idea_list in cluster_ideas.items():
            # Sample ideas (up to 10)
            sample_size = min(settings.cluster_sample_size, len(cluster_idea_list))
            sampled_ideas = np.random.choice(cluster_idea_list, sample_size, replace=False)
            sample_texts = [idea.formatted_text for idea in sampled_ideas]

            # Generate label
            label = await llm_service.summarize_cluster(
                sample_texts,
                custom_prompt=session.summarization_prompt
            )

            # Calculate convex hull
            cluster_coords = np.array([[idea.x, idea.y] for idea in cluster_idea_list])
            convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

            # Calculate average novelty score
            avg_novelty = sum(idea.novelty_score for idea in cluster_idea_list) / len(cluster_idea_list)

            # Update or create cluster
            cluster_result = await db.execute(
                select(Cluster).where(
                    Cluster.session_id == session_id,
                    Cluster.id == cluster_id
                )
            )
            cluster = cluster_result.scalar_one_or_none()

            if cluster:
                cluster.label = label
                cluster.convex_hull_points = convex_hull_points
                cluster.sample_idea_ids = [str(idea.id) for idea in sampled_ideas]
                cluster.idea_count = len(cluster_idea_list)
                cluster.avg_novelty_score = avg_novelty
            else:
                cluster = Cluster(
                    id=cluster_id,
                    session_id=session_id,
                    label=label,
                    convex_hull_points=convex_hull_points,
                    sample_idea_ids=[str(idea.id) for idea in sampled_ideas],
                    idea_count=len(cluster_idea_list),
                    avg_novelty_score=avg_novelty,
                )
                db.add(cluster)

        await db.commit()

        # Broadcast cluster updates via WebSocket
        cluster_data = [
            {
                "id": cluster_id,
                "label": cluster.label,
                "convex_hull": cluster.convex_hull_points,
                "idea_count": cluster.idea_count,
                "avg_novelty_score": cluster.avg_novelty_score,
            }
            for cluster_id, cluster in cluster_ideas.items()
        ]
        await manager.send_clusters_updated(session_id, cluster_data)

        # Broadcast coordinate updates (ideas were repositioned)
        coordinate_updates = [
            {
                "idea_id": str(idea.id),
                "x": idea.x,
                "y": idea.y,
                "cluster_id": idea.cluster_id,
            }
            for idea in ideas
        ]
        await manager.send_coordinates_updated(session_id, coordinate_updates)

    except Exception as e:
        # Log error but don't fail the main request
        print(f"Error updating cluster labels: {e}")


@router.get("/{session_id}", response_model=IdeaListResponse)
async def list_ideas(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> IdeaListResponse:
    """List all ideas in a session."""
    # Verify session exists
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all ideas with user information
    ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == session_id).order_by(Idea.created_at)
    )
    ideas = ideas_result.scalars().all()

    # Get user names
    user_result = await db.execute(
        select(User).where(User.session_id == session_id)
    )
    users = {user.user_id: user.name for user in user_result.scalars().all()}

    idea_responses = [
        IdeaResponse(
            id=idea.id,
            session_id=idea.session_id,
            user_id=idea.user_id,
            user_name=users.get(idea.user_id, "Unknown"),
            raw_text=idea.raw_text,
            formatted_text=idea.formatted_text,
            x=idea.x,
            y=idea.y,
            cluster_id=idea.cluster_id,
            novelty_score=idea.novelty_score,
            timestamp=idea.created_at,
        )
        for idea in ideas
    ]

    return IdeaListResponse(ideas=idea_responses, total=len(idea_responses))


@router.get("/{session_id}/{idea_id}", response_model=IdeaResponse)
async def get_idea(
    session_id: UUID,
    idea_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> IdeaResponse:
    """Get a specific idea."""
    result = await db.execute(
        select(Idea).where(
            Idea.session_id == session_id,
            Idea.id == idea_id
        )
    )
    idea = result.scalar_one_or_none()

    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )

    # Get user name
    user_result = await db.execute(
        select(User).where(
            User.session_id == session_id,
            User.user_id == idea.user_id
        )
    )
    user = user_result.scalar_one_or_none()

    return IdeaResponse(
        id=idea.id,
        session_id=idea.session_id,
        user_id=idea.user_id,
        user_name=user.name if user else "Unknown",
        raw_text=idea.raw_text,
        formatted_text=idea.formatted_text,
        x=idea.x,
        y=idea.y,
        cluster_id=idea.cluster_id,
        novelty_score=idea.novelty_score,
        timestamp=idea.created_at,
    )
