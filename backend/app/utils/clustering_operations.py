"""Clustering operation utilities for debug endpoints."""

import asyncio
import logging
from typing import Any

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.services.clustering import ClusteringService
from backend.app.services.llm import LLMService
from backend.app.utils.cluster_labeling import generate_simple_label

logger = logging.getLogger(__name__)


async def group_ideas_by_cluster(ideas: list[Idea]) -> dict[int, list[Idea]]:
    """
    Group ideas by their cluster ID.

    Args:
        ideas: List of ideas with cluster assignments

    Returns:
        Dictionary mapping cluster_id to list of ideas
    """
    cluster_ideas: dict[int, list[Idea]] = {}
    for idea in ideas:
        if idea.cluster_id is not None:
            if idea.cluster_id not in cluster_ideas:
                cluster_ideas[idea.cluster_id] = []
            cluster_ideas[idea.cluster_id].append(idea)
    return cluster_ideas


async def generate_cluster_labels_parallel(
    cluster_ideas: dict[int, list[Idea]],
    session: Session,
    llm_service: LLMService | None,
    use_llm: bool,
) -> list[tuple[int, str, list[Idea]]]:
    """
    Generate labels for all clusters in parallel.

    Args:
        cluster_ideas: Dictionary mapping cluster_id to list of ideas
        session: Session object for context
        llm_service: LLM service instance (optional)
        use_llm: Whether to use LLM for label generation

    Returns:
        List of tuples (cluster_id, label, sampled_ideas)
    """
    async def generate_label_for_cluster(
        cluster_id: int,
        cluster_idea_list: list[Idea]
    ) -> tuple[int, str, list[Idea]]:
        """Generate label for a single cluster (can run in parallel)."""
        # Sample ideas
        sample_size = min(10, len(cluster_idea_list))
        sampled_ideas = np.random.choice(cluster_idea_list, sample_size, replace=False).tolist()

        # Generate label
        if use_llm and llm_service:
            # Use LLM to generate cluster label
            logger.info(f"[CLUSTER-LABELS] Generating LLM label for cluster {cluster_id}")
            sample_texts = [idea.formatted_text for idea in sampled_ideas]
            label = await llm_service.summarize_cluster(
                sample_texts,
                custom_prompt=session.summarization_prompt,
                session_context=session.description
            )
            logger.info(f"[CLUSTER-LABELS] Generated LLM label for cluster {cluster_id}: {label}")
        else:
            # Simple label without LLM
            label = generate_simple_label(cluster_id)
            logger.info(f"[CLUSTER-LABELS] Using simple label for cluster {cluster_id}")

        return cluster_id, label, sampled_ideas

    # Generate all labels in parallel
    label_tasks = [
        generate_label_for_cluster(cluster_id, cluster_idea_list)
        for cluster_id, cluster_idea_list in cluster_ideas.items()
    ]
    return await asyncio.gather(*label_tasks)


async def create_or_update_clusters(
    db: AsyncSession,
    session_id: str,
    cluster_ideas: dict[int, list[Idea]],
    label_results: list[tuple[int, str, list[Idea]]],
    clustering_service: ClusteringService,
) -> None:
    """
    Create or update cluster records in database.

    Args:
        db: Database session
        session_id: Session ID
        cluster_ideas: Dictionary mapping cluster_id to list of ideas
        label_results: List of tuples (cluster_id, label, sampled_ideas)
        clustering_service: Clustering service for convex hull computation
    """
    for cluster_id, label, sampled_ideas in label_results:
        cluster_idea_list = cluster_ideas[cluster_id]

        # Calculate convex hull
        cluster_coords = np.array([[idea.x, idea.y] for idea in cluster_idea_list])
        convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

        # Calculate average novelty
        avg_novelty = (
            sum(idea.novelty_score for idea in cluster_idea_list)
            / len(cluster_idea_list)
        )

        # Create or update cluster
        cluster_result = await db.execute(
            select(Cluster).where(
                Cluster.session_id == session_id, Cluster.id == cluster_id
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


async def delete_existing_clusters(db: AsyncSession, session_id: str) -> None:
    """
    Delete all existing clusters for a session.

    Args:
        db: Database session
        session_id: Session ID
    """
    await db.execute(
        delete(Cluster).where(Cluster.session_id == session_id)
    )
    await db.commit()
    logger.info(f"[CLUSTERING] Deleted all existing clusters for session {session_id}")


async def update_idea_coordinates(
    db: AsyncSession,
    ideas: list[Idea],
    coordinates: np.ndarray,
    cluster_labels: np.ndarray,
) -> None:
    """
    Update idea coordinates and cluster assignments.

    Args:
        db: Database session
        ideas: List of ideas to update
        coordinates: 2D coordinates array
        cluster_labels: Cluster label array
    """
    for i, idea in enumerate(ideas):
        idea.x = float(coordinates[i, 0])
        idea.y = float(coordinates[i, 1])
        idea.cluster_id = int(cluster_labels[i])

    await db.commit()


def build_cluster_response(
    cluster_ideas: dict[int, list[Idea]],
    cluster_labels: dict[int, str],
) -> dict[int, dict[str, Any]]:
    """
    Build cluster response dictionary.

    Args:
        cluster_ideas: Dictionary mapping cluster_id to list of ideas
        cluster_labels: Dictionary mapping cluster_id to label

    Returns:
        Dictionary with cluster information
    """
    return {
        cluster_id: {
            "label": cluster_labels.get(cluster_id, generate_simple_label(cluster_id)),
            "idea_count": len(ideas),
        }
        for cluster_id, ideas in cluster_ideas.items()
    }
