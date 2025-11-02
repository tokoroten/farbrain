"""Cluster labeling utilities."""

import logging
from typing import Optional

from backend.app.models.idea import Idea
from backend.app.services.llm import LLMService

logger = logging.getLogger(__name__)


def generate_simple_label(cluster_id: int) -> str:
    """
    Generate a simple numeric label for a cluster.

    Args:
        cluster_id: Zero-based cluster ID

    Returns:
        Simple label like "クラスタ 1"
    """
    return f"クラスタ {cluster_id + 1}"


async def generate_cluster_label(
    cluster_id: int,
    ideas: list[Idea],
    llm_service: Optional[LLMService] = None,
    session_context: Optional[str] = None,
    use_llm: bool = False,
) -> str:
    """
    Generate a cluster label, optionally using LLM.

    Args:
        cluster_id: Zero-based cluster ID
        ideas: List of ideas in the cluster
        llm_service: LLM service instance (required if use_llm=True)
        session_context: Session description for context
        use_llm: Whether to use LLM for label generation

    Returns:
        Generated cluster label

    Raises:
        ValueError: If use_llm=True but llm_service is None
    """
    if not use_llm or llm_service is None:
        # Simple label without LLM
        label = generate_simple_label(cluster_id)
        logger.info(f"[CLUSTER-LABEL] Using simple label for cluster {cluster_id}")
        return label

    try:
        # Generate LLM label
        label = await llm_service.generate_cluster_summary(
            ideas=[idea.formatted_text for idea in ideas],
            session_context=session_context
        )
        logger.info(f"[CLUSTER-LABEL] Generated LLM label for cluster {cluster_id}: {label}")
        return label
    except Exception as e:
        # Fallback to simple label on error
        logger.error(f"[CLUSTER-LABEL] Failed to generate LLM label for cluster {cluster_id}: {e}")
        label = generate_simple_label(cluster_id)
        logger.info(f"[CLUSTER-LABEL] Using fallback simple label for cluster {cluster_id}")
        return label
