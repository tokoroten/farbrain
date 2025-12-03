"""Idea management API endpoints."""

import asyncio
import logging
import math
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    SessionNotFoundError,
    SessionNotAcceptingIdeasError,
    SessionEndedError,
    UserNotFoundError,
)
from backend.app.db.base import get_db
from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.schemas.idea import IdeaCreate, IdeaListResponse, IdeaResponse, IdeaDelete
from backend.app.services.clustering import get_clustering_service
from backend.app.services.embedding import EmbeddingService, get_embedding_service
from backend.app.services.llm import LLMService, get_llm_service
from backend.app.services.scoring import NoveltyScorer, min_distance_transform
from backend.app.websocket.manager import manager
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter(prefix="/ideas", tags=["ideas"])

# Logger
logger = logging.getLogger(__name__)

# Service instances
novelty_scorer = NoveltyScorer(min_distance_transform)

# Session-level locks for re-clustering (prevents concurrent re-clustering on same session)
_recluster_locks: dict[str, asyncio.Lock] = {}
_recluster_in_progress: set[str] = set()  # Track which sessions are currently re-clustering


# Helper functions for create_idea endpoint

async def _verify_session_and_user(
    session_id: str,
    user_id: str,
    db: AsyncSession
) -> tuple[Session, User]:
    """
    Verify that session exists and user is part of it.

    Args:
        session_id: Session ID to verify
        user_id: User ID to verify
        db: Database session

    Returns:
        Tuple of (Session, User)

    Raises:
        SessionNotFoundError: If session does not exist
        SessionNotAcceptingIdeasError: If session is not accepting new ideas
        SessionEndedError: If session has ended
        UserNotFoundError: If user not found in session
    """
    # Verify session
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise SessionNotFoundError(session_id)

    if not session.accepting_ideas:
        raise SessionNotAcceptingIdeasError(session_id)

    if session.status == "ended":
        raise SessionEndedError(session_id)

    # Verify user
    user_result = await db.execute(
        select(User).where(
            User.session_id == session_id,
            User.user_id == user_id
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise UserNotFoundError(user_id, session_id)

    return session, user


async def _format_and_embed_text(
    raw_text: str,
    skip_formatting: bool,
    session: Session,
    existing_ideas: list[Idea],
    preformatted_text: str | None = None
) -> tuple[str, np.ndarray]:
    """
    Format text with LLM (if needed) and generate embedding.

    If formatting is enabled, finds similar existing ideas and instructs LLM
    to generate a differentiated idea.

    Args:
        raw_text: Raw user input
        skip_formatting: Whether to skip LLM formatting
        session: Session object for context
        existing_ideas: List of existing ideas for similarity search
        preformatted_text: Pre-formatted text (e.g., from variation generation)

    Returns:
        Tuple of (formatted_text, embedding_array)
    """
    # Use pre-formatted text if provided
    if preformatted_text:
        formatted_text = preformatted_text
    elif skip_formatting:
        formatted_text = raw_text
    else:
        # Generate temporary embedding from raw text to find similar ideas
        similar_ideas_text = []
        if existing_ideas:
            temp_embedding = await get_embedding_service().embed(raw_text)
            existing_embeddings = np.array([idea.embedding for idea in existing_ideas])

            # Calculate similarities
            similarities = cosine_similarity(
                temp_embedding.reshape(1, -1),
                existing_embeddings
            )[0]

            # Get top 5 most similar ideas
            top_k = min(5, len(existing_ideas))
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            similar_ideas_text = [existing_ideas[idx].formatted_text for idx in top_indices]

        # Format with LLM, including similar ideas as context
        formatted_text = await get_llm_service().format_idea(
            raw_text,
            custom_prompt=session.formatting_prompt,
            session_context=session.description,
            similar_ideas=similar_ideas_text if similar_ideas_text else None
        )

    # Generate final embedding from formatted text
    embedding = await get_embedding_service().embed(formatted_text)
    return formatted_text, embedding


def _calculate_novelty_and_closest(
    embedding: np.ndarray,
    existing_ideas: list[Idea],
    current_user_id: str,
    penalize_self_similarity: bool = True
) -> tuple[float, str | None]:
    """
    Calculate novelty score and find closest existing idea.
    If penalize_self_similarity is True and the closest idea belongs to the same user,
    apply a 0.5x penalty.

    Args:
        embedding: Embedding vector of new idea
        existing_ideas: List of existing ideas in session
        current_user_id: User ID of the user submitting the new idea
        penalize_self_similarity: Whether to penalize similar ideas from same user

    Returns:
        Tuple of (novelty_score, closest_idea_id)
    """
    n_existing = len(existing_ideas)

    if n_existing == 0:
        return 100.0, None

    existing_embeddings = np.array([idea.embedding for idea in existing_ideas])

    # Calculate cosine similarities to find closest idea
    similarities = cosine_similarity(
        embedding.reshape(1, -1),
        existing_embeddings
    )[0]

    # Find closest idea (highest similarity = most similar)
    closest_idx = np.argmax(similarities)
    closest_idea = existing_ideas[closest_idx]
    closest_idea_id = str(closest_idea.id)

    # Calculate novelty score
    novelty_score = novelty_scorer.calculate_score(
        embedding.reshape(1, -1),
        existing_embeddings
    )

    # Apply 0.5x penalty if penalize_self_similarity is enabled and closest idea is from the same user
    if penalize_self_similarity and closest_idea.user_id == current_user_id:
        novelty_score *= 0.5
        logger.info(f"Applied 0.5x penalty: closest idea is from same user (score: {novelty_score:.2f})")

    return novelty_score, closest_idea_id


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
    # Step 1: Verify session and user
    session, user = await _verify_session_and_user(
        str(idea_data.session_id),
        str(idea_data.user_id),
        db
    )

    # Check if session is accepting new ideas
    if not session.accepting_ideas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このセッションは停止されているため、新しいアイデアを投稿できません"
        )

    # Step 2: Get existing ideas for scoring and clustering
    existing_ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == str(idea_data.session_id))
    )
    existing_ideas = existing_ideas_result.scalars().all()
    n_existing = len(existing_ideas)

    # Get session-specific clustering service
    clustering_service = get_clustering_service(
        str(idea_data.session_id),
        fixed_cluster_count=session.fixed_cluster_count
    )

    # Step 3: Format text and generate embedding
    formatted_text, embedding = await _format_and_embed_text(
        idea_data.raw_text,
        idea_data.skip_formatting,
        session,
        existing_ideas,
        preformatted_text=idea_data.formatted_text
    )
    embedding_list = embedding.tolist()

    # Step 4: Calculate novelty score and find closest idea
    novelty_score, closest_idea_id = _calculate_novelty_and_closest(
        embedding,
        existing_ideas,
        idea_data.user_id,
        session.penalize_self_similarity
    )

    # Extract existing embeddings for clustering
    existing_embeddings = np.array([idea.embedding for idea in existing_ideas]) if existing_ideas else np.array([])

    # Step 5: Assign coordinates
    need_cluster_update = False  # Flag to track if we need to update clusters
    coordinates_recalculated = False  # Flag to indicate UMAP re-fit occurred

    if n_existing < settings.min_ideas_for_clustering - 1:
        # Random coordinates for first 9 ideas
        x = float(np.random.uniform(-10, 10))
        y = float(np.random.uniform(-10, 10))
        cluster_id = None
    elif n_existing == settings.min_ideas_for_clustering - 1:
        # 10th idea: Fit UMAP on all 10 ideas for the first time
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

        # Mark that coordinates were recalculated
        coordinates_recalculated = True
        need_cluster_update = True
    else:
        # 11+ ideas: Use cached UMAP model's transform() method
        logger.info(f"[IDEA-CREATE] Processing idea #{n_existing + 1} for session {idea_data.session_id}")
        logger.info(f"[IDEA-CREATE] Clustering service UMAP model status: {'EXISTS' if clustering_service.umap_model is not None else 'NONE'}")

        # If model is not fitted (e.g., after server restart), assign random coordinates
        # and trigger full_recluster_session (which has proper locking)
        if clustering_service.umap_model is None:
            logger.warning(f"[IDEA-CREATE] UMAP model not found for session {idea_data.session_id}. Assigning random coordinates and triggering re-clustering...")

            # Assign random coordinates (will be updated by full_recluster_session)
            x = float(np.random.uniform(-10, 10))
            y = float(np.random.uniform(-10, 10))
            cluster_id = 0  # Temporary cluster, will be updated by re-clustering

            logger.info(f"[IDEA-CREATE] Assigned temporary random coordinates: ({x:.4f}, {y:.4f})")

            # Mark that coordinates need to be recalculated (triggers full_recluster_session later)
            coordinates_recalculated = True
        else:
            # Normal case: transform using existing model
            logger.info(f"[IDEA-CREATE] Using existing UMAP model to transform new idea")
            x, y = clustering_service.transform(embedding)
            logger.info(f"[IDEA-CREATE] Transformed coordinates: ({x:.4f}, {y:.4f})")

            # Predict cluster for the new coordinates
            cluster_id = clustering_service.predict_cluster((x, y))
            logger.info(f"[IDEA-CREATE] Predicted cluster: {cluster_id}")

    # Create idea
    idea = Idea(
        session_id=str(idea_data.session_id),
        user_id=str(idea_data.user_id),
        raw_text=idea_data.raw_text,
        formatted_text=formatted_text,
        embedding=embedding_list,
        x=x,
        y=y,
        cluster_id=cluster_id,
        novelty_score=novelty_score,
        closest_idea_id=closest_idea_id,
    )

    db.add(idea)

    # Update user score and count
    user.total_score += novelty_score
    user.idea_count += 1

    await db.commit()
    await db.refresh(idea)
    await db.refresh(user)

    # Update clusters if needed (after UMAP model re-fit)
    if need_cluster_update:
        logger.info(f"[IDEA-CREATE] Updating clusters after re-clustering")

        # Get all ideas including the new one
        all_ideas_result = await db.execute(
            select(Idea).where(Idea.session_id == str(idea_data.session_id))
        )
        all_ideas = all_ideas_result.scalars().all()

        # Group ideas by cluster
        cluster_ideas_map: dict[int, list[Idea]] = {}
        for idea_item in all_ideas:
            if idea_item.cluster_id is not None:
                if idea_item.cluster_id not in cluster_ideas_map:
                    cluster_ideas_map[idea_item.cluster_id] = []
                cluster_ideas_map[idea_item.cluster_id].append(idea_item)

        # Update or create clusters
        for cluster_id, cluster_idea_list in cluster_ideas_map.items():
            # Calculate convex hull
            cluster_coords = np.array([[idea_item.x, idea_item.y] for idea_item in cluster_idea_list])
            convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

            # Calculate average novelty score
            avg_novelty = sum(idea_item.novelty_score for idea_item in cluster_idea_list) / len(cluster_idea_list)

            # Get or create cluster
            cluster_result = await db.execute(
                select(Cluster).where(
                    Cluster.session_id == str(idea_data.session_id),
                    Cluster.id == cluster_id
                )
            )
            cluster = cluster_result.scalar_one_or_none()

            if cluster:
                # Update existing cluster
                cluster.convex_hull_points = convex_hull_points
                cluster.idea_count = len(cluster_idea_list)
                cluster.avg_novelty_score = avg_novelty
            else:
                # Create new cluster with simple label
                cluster = Cluster(
                    id=cluster_id,
                    session_id=str(idea_data.session_id),
                    label=f"クラスタ {cluster_id + 1}",
                    convex_hull_points=convex_hull_points,
                    sample_idea_ids=[str(idea_item.id) for idea_item in cluster_idea_list[:10]],
                    idea_count=len(cluster_idea_list),
                    avg_novelty_score=avg_novelty,
                )
                db.add(cluster)

        await db.commit()
        logger.info(f"[IDEA-CREATE] Updated {len(cluster_ideas_map)} clusters")

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
        closest_idea_id=idea.closest_idea_id,
        timestamp=idea.timestamp.isoformat(),
        coordinates_recalculated=coordinates_recalculated,
    )

    # Step 6: Trigger full re-clustering based on ideas since last clustering
    # Re-fetch actual idea count and session from DB after commit (important for parallel submissions)
    actual_count_result = await db.execute(
        select(Idea).where(Idea.session_id == str(idea_data.session_id))
    )
    actual_total = len(actual_count_result.scalars().all())

    # Re-fetch session to get latest last_clustered_idea_count
    await db.refresh(session)
    ideas_since_last_cluster = actual_total - session.last_clustered_idea_count
    logger.info(f"[IDEA-CREATE] Actual idea count: {actual_total}, last clustered at: {session.last_clustered_idea_count}, ideas since: {ideas_since_last_cluster}")

    if actual_total >= settings.min_ideas_for_clustering:
        # Trigger re-clustering if:
        # 1. Enough ideas have been added since last clustering, OR
        # 2. UMAP model doesn't exist (server restart case - coordinates_recalculated is True)
        should_recluster = (
            ideas_since_last_cluster >= settings.clustering_interval or
            (coordinates_recalculated and clustering_service.umap_model is None)
        )
        if should_recluster:
            logger.info(f"[IDEA-CREATE] Triggering full re-clustering (ideas_since_last_cluster={ideas_since_last_cluster}, umap_exists={clustering_service.umap_model is not None})")
            asyncio.create_task(
                full_recluster_session(str(idea_data.session_id))
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
        closest_idea_id=idea.closest_idea_id,
        timestamp=idea.timestamp,
    )


async def full_recluster_session(session_id: str) -> None:
    """Background task to fully re-cluster all ideas (UMAP re-fit + label update)."""
    from backend.app.db.base import AsyncSessionLocal

    # Check if re-clustering is already in progress for this session
    if session_id in _recluster_in_progress:
        logger.info(f"[RECLUSTER] Re-clustering already in progress for session {session_id}, skipping")
        return

    # Mark as in progress
    _recluster_in_progress.add(session_id)

    try:
        async with AsyncSessionLocal() as db:
            try:
                from backend.app.services.clustering import get_clustering_service

                logger.info(f"[RECLUSTER] Starting full re-clustering for session {session_id}")

                # Get session
                session_result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = session_result.scalar_one_or_none()
                if not session:
                    logger.error(f"[RECLUSTER] Session {session_id} not found")
                    return

                # Get all ideas
                ideas_result = await db.execute(
                    select(Idea).where(Idea.session_id == session_id)
                )
                ideas = ideas_result.scalars().all()

                if len(ideas) < settings.min_ideas_for_clustering:
                    logger.info(f"[RECLUSTER] Not enough ideas ({len(ideas)}) for clustering")
                    return

                # Get clustering service (DO NOT clear - keep existing instance to avoid race conditions)
                # fit_transform() will update the internal UMAP and k-means models
                clustering_service = get_clustering_service(
                    session_id,
                    fixed_cluster_count=session.fixed_cluster_count
                )

                # Get all embeddings
                all_embeddings = np.array([np.array(idea.embedding) for idea in ideas])

                # Perform full clustering (this will fit a new UMAP model)
                clustering_result = clustering_service.fit_transform(all_embeddings)

                # Update coordinates and cluster assignments
                for i, idea in enumerate(ideas):
                    idea.x = float(clustering_result.coordinates[i, 0])
                    idea.y = float(clustering_result.coordinates[i, 1])
                    idea.cluster_id = int(clustering_result.cluster_labels[i])

                # Update last_clustered_idea_count on session
                session.last_clustered_idea_count = len(ideas)

                await db.commit()

                logger.info(f"[RECLUSTER] Re-clustered {len(ideas)} ideas into {clustering_result.n_clusters} clusters, updated last_clustered_idea_count to {len(ideas)}")

                # Now update cluster labels (this also sends clusters_recalculated via WebSocket)
                await update_cluster_labels(session_id, db)

                logger.info(f"[RECLUSTER] Full re-clustering complete for session {session_id}")

            except Exception as e:
                logger.error(f"[RECLUSTER] Failed to re-cluster session {session_id}: {e}", exc_info=True)
    finally:
        # Always remove from in-progress set
        _recluster_in_progress.discard(session_id)


async def update_cluster_labels(session_id: str, db: AsyncSession) -> None:
    """Background task to update cluster labels using LLM (without re-clustering)."""
    try:
        # Get session for custom prompts
        session_result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            return

        # Get clustering service for this session
        clustering_service = get_clustering_service(
            session_id,
            fixed_cluster_count=session.fixed_cluster_count
        )

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

        # Generate labels for each cluster in parallel
        async def generate_label_for_cluster(cluster_id: int, cluster_idea_list: list[Idea]) -> tuple[int, str, list[Idea]]:
            """Generate label for a single cluster (can run in parallel)."""
            # Sample ideas (up to 10)
            sample_size = min(settings.cluster_sample_size, len(cluster_idea_list))
            sampled_ideas = np.random.choice(cluster_idea_list, sample_size, replace=False).tolist()
            sample_texts = [idea.formatted_text for idea in sampled_ideas]

            # Generate label (with session context)
            label = await get_llm_service().summarize_cluster(
                sample_texts,
                custom_prompt=session.summarization_prompt,
                session_context=session.description
            )

            return cluster_id, label, sampled_ideas

        # Generate all labels in parallel
        label_tasks = [
            generate_label_for_cluster(cluster_id, cluster_idea_list)
            for cluster_id, cluster_idea_list in cluster_ideas.items()
        ]
        label_results = await asyncio.gather(*label_tasks)

        # Update clusters with generated labels
        for cluster_id, label, sampled_ideas in label_results:
            cluster_idea_list = cluster_ideas[cluster_id]

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

        # Broadcast clusters_recalculated event to trigger frontend to fetch fresh data from API
        # This ensures data format consistency (single source of truth from API)
        logger.info(f"[CLUSTER-LABELS] Broadcasting clusters_recalculated event to session {session_id}")
        await manager.send_clusters_recalculated(session_id)

    except Exception as e:
        # Log error but don't fail the main request
        logger.error(f"[CLUSTER-LABELS] Error updating cluster labels for session {session_id}: {e}", exc_info=True)


@router.get("/{session_id}", response_model=IdeaListResponse)
async def list_ideas(
    session_id: str,
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
        select(Idea).where(Idea.session_id == session_id).order_by(Idea.timestamp)
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
            closest_idea_id=idea.closest_idea_id,
            timestamp=idea.timestamp,
        )
        for idea in ideas
    ]

    return IdeaListResponse(ideas=idea_responses, total=len(idea_responses))


@router.get("/{session_id}/{idea_id}", response_model=IdeaResponse)
async def get_idea(
    session_id: str,
    idea_id: str,
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
        closest_idea_id=idea.closest_idea_id,
        timestamp=idea.timestamp,
    )


@router.delete("/{idea_id}", status_code=status.HTTP_200_OK)
async def delete_idea(
    idea_id: str,
    delete_data: IdeaDelete,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete an idea.

    Users can delete their own ideas.
    Admins can delete any idea by providing the admin password.
    """
    logger.info(f"[DELETE-IDEA] Request to delete idea {idea_id} by user {delete_data.user_id}")

    # Get the idea
    result = await db.execute(
        select(Idea).where(Idea.id == idea_id)
    )
    idea = result.scalar_one_or_none()

    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found"
        )

    # Check permissions
    is_owner = str(idea.user_id) == str(delete_data.user_id)
    is_admin = delete_data.admin_password == settings.admin_password

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own ideas, or use admin password to delete others' ideas"
        )

    session_id = idea.session_id
    user_id = idea.user_id

    # Delete the idea
    await db.delete(idea)

    # Update user's idea count and total score
    user_result = await db.execute(
        select(User).where(
            User.session_id == session_id,
            User.user_id == user_id
        )
    )
    user = user_result.scalar_one_or_none()

    if user:
        # Recalculate user's total score and idea count
        ideas_result = await db.execute(
            select(Idea).where(
                Idea.session_id == session_id,
                Idea.user_id == user_id
            )
        )
        remaining_ideas = ideas_result.scalars().all()

        user.idea_count = len(remaining_ideas)
        user.total_score = sum(idea.novelty_score for idea in remaining_ideas)
        db.add(user)

    await db.commit()

    logger.info(f"[DELETE-IDEA] Successfully deleted idea {idea_id}")

    # Notify all clients in the session via WebSocket
    await manager.broadcast_to_session(
        session_id=str(session_id),
        message={
            "type": "idea_deleted",
            "data": {
                "idea_id": str(idea_id),
                "user_id": str(user_id),
            }
        }
    )

    # Send updated scoreboard
    # Fetch all users with updated scores
    users_result = await db.execute(
        select(User).where(User.session_id == session_id).order_by(User.total_score.desc())
    )
    users = users_result.scalars().all()

    rankings = [
        {
            "user_id": user.user_id,
            "name": user.name,
            "total_score": user.total_score,
            "idea_count": user.idea_count,
        }
        for user in users
    ]

    await manager.send_scoreboard_updated(session_id=str(session_id), rankings=rankings)

    return {"message": "Idea deleted successfully", "idea_id": idea_id}
