"""
Dialogue API for idea deepening through interactive conversation.

Provides streaming and non-streaming endpoints for engaging users in dialogue to refine ideas.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.services.llm import get_llm_service

router = APIRouter(prefix="/api/dialogue", tags=["dialogue"])


class DialogueRequest(BaseModel):
    """Request for dialogue interaction."""

    message: str
    conversation_history: list[dict[str, str]] | None = None
    session_id: str | None = None  # Optional session ID for context


class VariationRequest(BaseModel):
    """Request for generating variations of an idea."""

    keyword: str
    session_id: str
    count: int = 10


@router.post("/deepen")
async def deepen_idea(
    request: DialogueRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Start or continue a dialogue to deepen an idea.

    Args:
        request: Dialogue request with message and history
        db: Database session

    Returns:
        Streaming response with LLM-generated questions/feedback

    Raises:
        HTTPException: If message is empty or LLM fails
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get session context if session_id provided
    session_context = None
    if request.session_id:
        session_result = await db.execute(
            select(Session).where(Session.id == request.session_id)
        )
        session = session_result.scalar_one_or_none()
        if session:
            # Check if session is accepting new ideas
            if not session.accepting_ideas:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="このセッションは停止されているため、新しいアイデアを投稿できません"
                )
            session_context = session.description

    llm_service = get_llm_service()

    async def generate():
        """Generate streaming response."""
        try:
            async for chunk in llm_service.deepen_idea(
                raw_text=request.message,
                conversation_history=request.conversation_history,
                session_context=session_context,
            ):
                # Send as Server-Sent Events format
                yield f"data: {chunk}\n\n"

            # Send completion signal
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/deepen-with-proposal")
async def deepen_idea_with_proposal(
    request: DialogueRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Dialogue deepening with intelligent proposal system using Tool Use.

    Returns either:
    - {"type": "question", "content": "..."} - Continue dialogue
    - {"type": "proposal", "content": "...", "verbalized_idea": "..."} - Propose submission

    Args:
        request: Dialogue request with message and history
        db: Database session

    Returns:
        Dict with type and content (and verbalized_idea if proposal)

    Raises:
        HTTPException: If message is empty or LLM fails
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get session context if session_id provided
    session_context = None
    if request.session_id:
        session_result = await db.execute(
            select(Session).where(Session.id == request.session_id)
        )
        session = session_result.scalar_one_or_none()
        if session:
            # Check if session is accepting new ideas
            if not session.accepting_ideas:
                raise HTTPException(
                    status_code=403,
                    detail="このセッションは停止されているため、新しいアイデアを投稿できません"
                )
            session_context = session.description

    llm_service = get_llm_service()

    try:
        result = await llm_service.deepen_idea_with_tools(
            raw_text=request.message,
            conversation_history=request.conversation_history,
            session_context=session_context,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deepen idea: {str(e)}",
        )


@router.post("/finalize")
async def finalize_idea(
    request: DialogueRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Finalize an idea after dialogue by generating formatted version.

    Args:
        request: Final dialogue state
        db: Database session

    Returns:
        Formatted idea and conversation summary

    Raises:
        HTTPException: If message is empty or LLM fails
    """
    # Get session context if session_id provided
    session_context = None
    if request.session_id:
        session_result = await db.execute(
            select(Session).where(Session.id == request.session_id)
        )
        session = session_result.scalar_one_or_none()
        if session:
            # Check if session is accepting new ideas
            if not session.accepting_ideas:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="このセッションは停止されているため、新しいアイデアを投稿できません"
                )
            session_context = session.description

    llm_service = get_llm_service()

    try:
        # If message is empty, synthesize idea from conversation history
        if not request.message.strip():
            if not request.conversation_history:
                raise HTTPException(
                    status_code=400,
                    detail="Either message or conversation_history must be provided"
                )

            # Synthesize idea from conversation
            formatted = await llm_service.synthesize_idea_from_conversation(
                conversation_history=request.conversation_history,
                session_context=session_context
            )

            return {
                "formatted_idea": formatted,
                "original_message": "",
                "from_conversation": True,
            }

        # Use the regular format_idea method to create final version (with context)
        formatted = await llm_service.format_idea(
            raw_text=request.message,
            session_context=session_context
        )

        return {
            "formatted_idea": formatted,
            "original_message": request.message,
            "from_conversation": False,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to finalize idea: {str(e)}",
        )


@router.post("/variations")
async def generate_variations(
    request: VariationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate variations of an idea keyword.

    Args:
        request: Variation request with keyword and count
        db: Database session

    Returns:
        List of generated idea variations

    Raises:
        HTTPException: If session not found or LLM fails
    """
    # Get session context
    session_result = await db.execute(
        select(Session).where(Session.id == request.session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )

    # Check if session is accepting new ideas
    if not session.accepting_ideas:
        raise HTTPException(
            status_code=403,
            detail="このセッションは停止されているため、新しいアイデアを投稿できません"
        )

    llm_service = get_llm_service()

    try:
        variations = await llm_service.generate_variations(
            keyword=request.keyword,
            session_context=session.description,
            count=request.count
        )

        return {
            "variations": variations
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate variations: {str(e)}",
        )
