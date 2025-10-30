"""Report generation API endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.session import Session
from backend.app.models.idea import Idea
from backend.app.models.user import User
from backend.app.models.cluster import Cluster
from backend.app.models.report import Report
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.pdf_generator import PDFGenerator

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)

# Global report generator instance
_report_generator: ReportGenerator | None = None
_pdf_generator: PDFGenerator | None = None

# Lock for report generation (prevents parallel generation for same session)
_report_generation_locks: dict[str, bool] = {}


def get_report_generator() -> ReportGenerator:
    """Get or create report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


def get_pdf_generator() -> PDFGenerator:
    """Get or create PDF generator instance."""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = PDFGenerator()
    return _pdf_generator


async def generate_report_markdown(
    session_id: UUID,
    db: AsyncSession,
) -> tuple[str, str]:
    """
    Generate Markdown report content.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Tuple of (markdown_content, session_title)

    Raises:
        HTTPException: If session not found
    """
    logger.info(f"[REPORT] Generating Markdown report for session {session_id}")

    # Verify session exists
    session_result = await db.execute(
        select(Session).where(Session.id == str(session_id))
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get all ideas
    ideas_result = await db.execute(
        select(Idea)
        .where(Idea.session_id == str(session_id))
        .order_by(Idea.novelty_score.desc())
    )
    ideas = ideas_result.scalars().all()
    current_idea_count = len(ideas)

    # Check for cached report
    cached_report_result = await db.execute(
        select(Report)
        .where(Report.session_id == str(session_id))
        .where(Report.status == "completed")
        .where(Report.markdown_content.isnot(None))
        .order_by(Report.created_at.desc())
    )
    cached_report = cached_report_result.scalar_one_or_none()

    # Return cached report if idea count hasn't changed
    if cached_report and cached_report.idea_count_at_generation == current_idea_count:
        logger.info(f"[REPORT] Using cached report (idea count: {current_idea_count})")
        return cached_report.markdown_content, session.title

    # Get all users
    users_result = await db.execute(
        select(User).where(User.session_id == str(session_id))
    )
    users_dict = {user.user_id: user for user in users_result.scalars().all()}

    # Get all clusters
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.session_id == str(session_id))
    )
    clusters_dict = {cluster.id: cluster for cluster in clusters_result.scalars().all()}

    # Generate LLM analysis
    report_generator = get_report_generator()
    cluster_insights = []

    # Analyze each cluster in parallel
    import asyncio

    async def analyze_single_cluster(cluster):
        cluster_ideas = [idea for idea in ideas if idea.cluster_id == cluster.id]
        if not cluster_ideas:
            return None

        # Prepare ideas data for analysis
        ideas_data = []
        for idea in cluster_ideas:
            user = users_dict.get(idea.user_id)
            user_name = user.name if user else "Unknown"
            ideas_data.append({
                "formatted_text": idea.formatted_text,
                "novelty_score": idea.novelty_score,
                "user_name": user_name,
            })

        analysis = await report_generator.analyze_cluster(
            cluster_label=cluster.label,
            ideas=ideas_data,
            session_theme=session.title,
            participant_count=len(users_dict),
        )

        return {
            "cluster_id": cluster.id,
            "label": cluster.label,
            "idea_count": len(cluster_ideas),
            "avg_score": cluster.avg_novelty_score,
            "analysis": analysis,
        }

    # Run cluster analysis in parallel
    if clusters_dict:
        logger.info(f"[REPORT] Analyzing {len(clusters_dict)} clusters in parallel")
        cluster_analysis_tasks = [
            analyze_single_cluster(cluster)
            for cluster in clusters_dict.values()
        ]
        cluster_insights = await asyncio.gather(*cluster_analysis_tasks)
        # Filter out None results
        cluster_insights = [insight for insight in cluster_insights if insight is not None]

    # Generate overall conclusion
    overall_conclusion = ""
    if cluster_insights and ideas:
        logger.info("[REPORT] Generating overall conclusion")

        overall_conclusion = await report_generator.generate_overall_conclusion(
            session_theme=session.title,
            participant_count=len(users_dict),
            total_ideas=len(ideas),
            cluster_count=len(clusters_dict),
            cluster_insights=cluster_insights,
        )

    # Build Markdown content
    md_lines = []

    # Title
    md_lines.append(f"# ブレインストーミングセッション レポート")
    md_lines.append("")
    md_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    md_lines.append("")

    # Session Overview
    md_lines.append("## 📊 セッション概要")
    md_lines.append("")
    md_lines.append(f"**テーマ**: {session.title}")
    if session.description:
        md_lines.append(f"**説明**: {session.description}")
    md_lines.append(f"**実施期間**: {session.start_time.strftime('%Y/%m/%d %H:%M')} - {session.ended_at.strftime('%Y/%m/%d %H:%M') if session.ended_at else '進行中'}")
    md_lines.append(f"**参加者数**: {len(users_dict)}名")
    md_lines.append(f"**総アイディア数**: {len(ideas)}件")
    md_lines.append(f"**テーマ（クラスタ）数**: {len(clusters_dict)}個")

    md_lines.append("")
    md_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    md_lines.append("")

    # Overall Conclusion (if available)
    if overall_conclusion:
        md_lines.append("## 🔍 セッション全体の総括")
        md_lines.append("")
        md_lines.append(overall_conclusion)
        md_lines.append("")
        md_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        md_lines.append("")

    # Ranking
    md_lines.append("## 🏆 貢献度ランキング")
    md_lines.append("")

    # Sort users by total score
    users_list = sorted(
        [u for u in users_dict.values() if u.idea_count > 0],
        key=lambda u: u.total_score,
        reverse=True
    )

    md_lines.append("| 順位 | 参加者名 | 投稿数 | 合計スコア | 平均スコア |")
    md_lines.append("|------|----------|--------|------------|------------|")

    for rank, user in enumerate(users_list, 1):
        avg_score = user.total_score / user.idea_count if user.idea_count > 0 else 0
        md_lines.append(f"| {rank} | {user.name} | {user.idea_count}件 | {user.total_score:.1f}点 | {avg_score:.1f}点 |")

    md_lines.append("")
    md_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    md_lines.append("")

    # Clusters
    if clusters_dict:
        md_lines.append("## 🎨 発見されたテーマ（クラスタ）")
        md_lines.append("")

        # Create a mapping from cluster_id to insights
        insights_by_cluster_id = {insight["cluster_id"]: insight for insight in cluster_insights}

        for cluster in sorted(clusters_dict.values(), key=lambda c: c.idea_count, reverse=True):
            md_lines.append(f"### テーマ{cluster.id + 1}: {cluster.label}")
            md_lines.append("")
            md_lines.append(f"**アイディア数**: {cluster.idea_count}件")
            md_lines.append(f"**平均スコア**: {cluster.avg_novelty_score:.2f}点")
            md_lines.append("")

            # Get ideas in this cluster
            cluster_ideas = [idea for idea in ideas if idea.cluster_id == cluster.id]
            cluster_ideas.sort(key=lambda i: i.novelty_score, reverse=True)

            if cluster_ideas:
                md_lines.append("**代表的なアイディア TOP 3**:")
                md_lines.append("")
                for i, idea in enumerate(cluster_ideas[:3], 1):
                    user = users_dict.get(idea.user_id)
                    user_name = user.name if user else "Unknown"
                    md_lines.append(f"{i}. **{idea.formatted_text}** ({idea.novelty_score:.1f}点 / {user_name})")
                    md_lines.append("")

            # Add LLM analysis if available
            insight = insights_by_cluster_id.get(cluster.id)
            if insight and insight["analysis"]:
                md_lines.append("**📊 AI分析**:")
                md_lines.append("")
                md_lines.append(insight["analysis"])
                md_lines.append("")

            md_lines.append("---")
            md_lines.append("")

    # Top Ideas
    md_lines.append("## 💎 最も独創的だったアイディア TOP 20")
    md_lines.append("")

    for i, idea in enumerate(ideas[:20], 1):
        user = users_dict.get(idea.user_id)
        user_name = user.name if user else "Unknown"
        cluster = clusters_dict.get(idea.cluster_id) if idea.cluster_id is not None else None
        cluster_label = cluster.label if cluster else "未分類"

        md_lines.append(f"### {i}位: {idea.novelty_score:.1f}点")
        md_lines.append("")
        md_lines.append(f"**投稿者**: {user_name}")
        md_lines.append(f"**テーマ**: {cluster_label}")
        md_lines.append("")
        md_lines.append(f"> {idea.formatted_text}")
        md_lines.append("")

        if idea.raw_text != idea.formatted_text:
            md_lines.append(f"*元のテキスト*: {idea.raw_text}")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    # All Ideas (Appendix)
    md_lines.append("## 📋 全アイディア一覧")
    md_lines.append("")
    md_lines.append("| No. | スコア | テーマ | 投稿者 | アイディア |")
    md_lines.append("|-----|--------|--------|--------|------------|")

    for i, idea in enumerate(ideas, 1):
        user = users_dict.get(idea.user_id)
        user_name = user.name if user else "Unknown"
        cluster = clusters_dict.get(idea.cluster_id) if idea.cluster_id is not None else None
        cluster_label = cluster.label if cluster else "未分類"

        # Truncate long text for table
        text = idea.formatted_text[:50] + "..." if len(idea.formatted_text) > 50 else idea.formatted_text
        md_lines.append(f"| {i} | {idea.novelty_score:.1f} | {cluster_label} | {user_name} | {text} |")

    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"*レポート生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}*")

    # Join all lines
    markdown_content = "\n".join(md_lines)

    logger.info(f"[REPORT] Successfully generated report with {len(ideas)} ideas")

    # Save to cache
    try:
        new_report = Report(
            session_id=str(session_id),
            status="completed",
            markdown_content=markdown_content,
            idea_count_at_generation=current_idea_count,
            completed_at=datetime.utcnow(),
        )
        db.add(new_report)
        await db.commit()
        logger.info(f"[REPORT] Cached report for session {session_id} (idea count: {current_idea_count})")
    except Exception as e:
        logger.error(f"[REPORT] Failed to cache report: {e}")
        # Continue even if caching fails

    return markdown_content, session.title


@router.get("/{session_id}/markdown")
async def download_markdown_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download Markdown report for a session."""
    session_id_str = str(session_id)

    # Check if report generation is already in progress
    if _report_generation_locks.get(session_id_str, False):
        logger.warning(f"[REPORT] Report generation already in progress for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="レポートを現在作成中です。完了するまでお待ちください。"
        )

    # Acquire lock
    _report_generation_locks[session_id_str] = True
    logger.info(f"[REPORT] Acquired report generation lock for session {session_id}")

    try:
        markdown_content, session_title = await generate_report_markdown(session_id, db)

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{session_title}_{timestamp}.md"

        # Return as downloadable file
        from urllib.parse import quote
        filename_encoded = quote(filename)

        return Response(
            content=markdown_content.encode('utf-8'),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}",
            }
        )
    finally:
        # Always release the lock
        _report_generation_locks[session_id_str] = False
        logger.info(f"[REPORT] Released report generation lock for session {session_id}")


@router.get("/{session_id}/pdf")
async def download_pdf_report(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and download PDF report for a session."""
    session_id_str = str(session_id)

    # Check if report generation is already in progress
    if _report_generation_locks.get(session_id_str, False):
        logger.warning(f"[REPORT] Report generation already in progress for session {session_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="レポートを現在作成中です。完了するまでお待ちください。"
        )

    # Acquire lock
    _report_generation_locks[session_id_str] = True
    logger.info(f"[REPORT] Acquired report generation lock for session {session_id}")

    try:
        # Generate markdown content
        markdown_content, session_title = await generate_report_markdown(session_id, db)

        # Convert to PDF
        pdf_generator = get_pdf_generator()
        pdf_bytes = pdf_generator.markdown_to_pdf(markdown_content)

        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{session_title}_{timestamp}.pdf"

        # Return as downloadable file
        from urllib.parse import quote
        filename_encoded = quote(filename)

        logger.info(f"[REPORT] Successfully generated PDF report for session {session_id}")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}",
            }
        )
    finally:
        # Always release the lock
        _report_generation_locks[session_id_str] = False
        logger.info(f"[REPORT] Released report generation lock for session {session_id}")
