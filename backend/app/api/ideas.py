"""Idea management API endpoints."""

import asyncio
import logging
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
from backend.app.services.clustering import get_clustering_service
from backend.app.services.embedding import EmbeddingService
from backend.app.services.llm import LLMService
from backend.app.services.scoring import NoveltyScorer, min_distance_transform
from backend.app.websocket.manager import manager
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter(prefix="/ideas", tags=["ideas"])

# Logger
logger = logging.getLogger(__name__)

# Service singletons
embedding_service = EmbeddingService()
llm_service = LLMService()
novelty_scorer = NoveltyScorer(min_distance_transform)


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
    # デバッグログ
    print(f"[DEBUG-PRINT] create_idea called: session={idea_data.session_id}, user={idea_data.user_id}")
    logger.error(f"[DEBUG-ERROR] create_idea called: session={idea_data.session_id}, user={idea_data.user_id}")

    # Verify session
    session_result = await db.execute(
        select(Session).where(Session.id == str(idea_data.session_id))
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
            User.session_id == str(idea_data.session_id),
            User.user_id == str(idea_data.user_id)
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this session"
        )

    # Get existing ideas for scoring and clustering
    print(f"[DEBUG-PRINT] Fetching existing ideas for session_id: {idea_data.session_id} (type: {type(idea_data.session_id)})")
    logger.error(f"[DEBUG-ERROR] About to execute SELECT query for session_id: {idea_data.session_id}")

    existing_ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == str(idea_data.session_id))
    )
    existing_ideas = existing_ideas_result.scalars().all()
    n_existing = len(existing_ideas)

    print(f"[DEBUG-PRINT] Found {n_existing} existing ideas")
    logger.error(f"[DEBUG-ERROR] Query returned {n_existing} ideas")
    if n_existing > 0:
        logger.error(f"[DEBUG-ERROR] First idea session_id: {existing_ideas[0].session_id} (type: {type(existing_ideas[0].session_id)})")

    # Get session-specific clustering service
    clustering_service = get_clustering_service(
        str(idea_data.session_id),
        fixed_cluster_count=session.fixed_cluster_count
    )

    # Step 1: Format idea with LLM (with session context) - skip if requested
    if idea_data.skip_formatting:
        formatted_text = idea_data.raw_text
    else:
        formatted_text = await llm_service.format_idea(
            idea_data.raw_text,
            custom_prompt=session.formatting_prompt,
            session_context=session.description
        )

    # Step 2: Generate embedding
    embedding = await embedding_service.embed(formatted_text)
    embedding_list = embedding.tolist()

    # Step 3: Calculate novelty score and find closest idea
    closest_idea_id = None
    if n_existing == 0:
        novelty_score = 100.0  # First idea gets max score
    else:
        existing_embeddings = np.array([idea.embedding for idea in existing_ideas])

        # Calculate cosine similarities to find closest idea
        similarities = cosine_similarity(
            embedding.reshape(1, -1),
            existing_embeddings
        )[0]

        # Find closest idea (highest similarity = most similar)
        closest_idx = np.argmax(similarities)
        closest_idea_id = str(existing_ideas[closest_idx].id)

        # Calculate novelty score
        novelty_score = novelty_scorer.calculate_score(
            embedding.reshape(1, -1),
            existing_embeddings
        )

    # Step 4: Assign coordinates
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

        # If model is not fitted (e.g., after server restart), re-cluster everything
        if clustering_service.umap_model is None:
            logger.warning(f"[IDEA-CREATE] UMAP model not found for session {idea_data.session_id}. Re-clustering all ideas...")

            # Get all existing ideas + new embedding
            all_embeddings = np.vstack([existing_embeddings, embedding.reshape(1, -1)])
            logger.info(f"[IDEA-CREATE] Re-clustering {len(all_embeddings)} ideas (including new one)")

            clustering_result = clustering_service.fit_transform(all_embeddings)

            # Get coordinates for new idea (last one)
            x = float(clustering_result.coordinates[-1, 0])
            y = float(clustering_result.coordinates[-1, 1])
            cluster_id = int(clustering_result.cluster_labels[-1])

            logger.info(f"[IDEA-CREATE] New idea coordinates after re-clustering: ({x:.4f}, {y:.4f}), cluster={cluster_id}")

            # Update coordinates for all existing ideas
            for i, idea in enumerate(existing_ideas):
                idea.x = float(clustering_result.coordinates[i, 0])
                idea.y = float(clustering_result.coordinates[i, 1])
                idea.cluster_id = int(clustering_result.cluster_labels[i])

            logger.info(f"[IDEA-CREATE] Re-clustering complete. Updated {len(existing_ideas)} existing ideas.")

            # Mark that we need to update clusters after creating the new idea
            need_cluster_update = True
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

    # Step 6: Trigger re-clustering or label update if needed
    new_total = n_existing + 1
    if new_total >= settings.min_ideas_for_clustering:
        # Full re-clustering every reclustering_interval ideas (e.g., every 50 ideas)
        if new_total % settings.reclustering_interval == 0:
            logger.info(f"[IDEA-CREATE] Triggering full re-clustering at {new_total} ideas")
            asyncio.create_task(
                full_recluster_session(idea_data.session_id, db)
            )
        # Label update only every clustering_interval ideas (e.g., every 10 ideas)
        elif new_total % settings.clustering_interval == 0:
            logger.info(f"[IDEA-CREATE] Triggering label update at {new_total} ideas")
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
        closest_idea_id=idea.closest_idea_id,
        timestamp=idea.timestamp,
    )


async def full_recluster_session(session_id: str, db: AsyncSession) -> None:
    """Background task to fully re-cluster all ideas (UMAP re-fit + label update)."""
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

        await db.commit()

        logger.info(f"[RECLUSTER] Re-clustered {len(ideas)} ideas into {clustering_result.n_clusters} clusters")

        # Now update cluster labels
        await update_cluster_labels(session_id, db)

        # Broadcast reclustering complete via WebSocket
        await manager.broadcast_to_session(
            session_id=session_id,
            message={
                "type": "reclustering_complete",
                "cluster_count": clustering_result.n_clusters,
                "idea_count": len(ideas),
            }
        )

        logger.info(f"[RECLUSTER] Full re-clustering complete for session {session_id}")

    except Exception as e:
        logger.error(f"[RECLUSTER] Failed to re-cluster session {session_id}: {e}", exc_info=True)


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
            label = await llm_service.summarize_cluster(
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
