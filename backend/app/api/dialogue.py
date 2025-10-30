"""
Dialogue API for idea deepening through interactive conversation.

Provides streaming endpoints for engaging users in dialogue to refine ideas.
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
