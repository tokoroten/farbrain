"""Debug API endpoints for development and testing."""

import asyncio
import logging
import uuid
import random
from datetime import datetime
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.base import get_db
from backend.app.models.cluster import Cluster
from backend.app.models.idea import Idea
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.vote import Vote
from backend.app.services.clustering import (
    ClusteringService,
    get_clustering_service,
    clear_clustering_service,
)
from backend.app.services.embedding import EmbeddingService
from backend.app.services.scoring import NoveltyScorer
from backend.app.services.llm import get_llm_service
from backend.app.utils.cluster_labeling import generate_simple_label, generate_cluster_label
from backend.app.utils.clustering_operations import (
    group_ideas_by_cluster,
    generate_cluster_labels_parallel,
    create_or_update_clusters,
    delete_existing_clusters,
    update_idea_coordinates,
    build_cluster_response,
)
from backend.app.services.starter_ideas import STARTER_IDEA_TEMPLATES
from backend.app.websocket.manager import manager

router = APIRouter(prefix="/debug", tags=["debug"])
logger = logging.getLogger(__name__)

# Global lock for clustering operations (per session)
_clustering_locks: dict[str, bool] = {}


class BulkIdeaCreate(BaseModel):
    """Bulk idea creation without LLM formatting."""

    session_id: str
    user_id: str
    ideas: list[str]  # List of raw idea texts


@router.post("/bulk-ideas", status_code=status.HTTP_201_CREATED)
async def create_bulk_ideas(
    data: BulkIdeaCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create multiple ideas at once without LLM formatting.

    This is a debug endpoint that skips LLM formatting and directly uses
    the raw text as formatted text. Useful for testing and demos.
    """
    # Verify session
    session_result = await db.execute(
        select(Session).where(Session.id == data.session_id)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Verify user
    user_result = await db.execute(
        select(User).where(
            User.session_id == data.session_id, User.user_id == data.user_id
        )
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this session",
        )

    # Get existing ideas
    existing_ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == data.session_id)
    )
    existing_ideas = existing_ideas_result.scalars().all()

    # Initialize services
    embedding_service = EmbeddingService()
    clustering_service = ClusteringService()
    novelty_scorer = NoveltyScorer()

    # Create ideas without LLM formatting
    created_ideas = []
    all_embeddings = [np.array(idea.embedding) for idea in existing_ideas]

    for raw_text in data.ideas:
        # Use raw text as formatted text (skip LLM)
        formatted_text = raw_text

        # Generate embedding
        embedding = await embedding_service.embed(formatted_text)
        embedding_list = embedding.tolist()
        all_embeddings.append(embedding)

        # Calculate novelty score and find closest idea
        closest_idea_id = None
        if len(all_embeddings) == 1:
            novelty_score = 100.0
        else:
            existing_embeddings = np.array(all_embeddings[:-1])
            novelty_score = novelty_scorer.calculate_score(
                embedding.reshape(1, -1), existing_embeddings
            )

            # Find closest idea (highest similarity)
            similarities = cosine_similarity(
                embedding.reshape(1, -1),
                existing_embeddings
            )[0]
            closest_idx = np.argmax(similarities)
            closest_idea = created_ideas[closest_idx]
            closest_idea_id = str(closest_idea.id)

            # Apply 0.5x penalty if closest idea is from the same user
            if closest_idea.user_id == data.user_id:
                novelty_score *= 0.5

        # Random coordinates for now
        x = float(np.random.uniform(-10, 10))
        y = float(np.random.uniform(-10, 10))

        idea = Idea(
            session_id=data.session_id,
            user_id=data.user_id,
            raw_text=raw_text,
            formatted_text=formatted_text,
            embedding=embedding_list,
            x=x,
            y=y,
            cluster_id=None,
            novelty_score=novelty_score,
            closest_idea_id=closest_idea_id,
        )

        db.add(idea)
        created_ideas.append(idea)

    # Update user stats
    user.idea_count += len(created_ideas)
    user.total_score += sum(idea.novelty_score for idea in created_ideas)

    await db.commit()

    # Refresh all ideas
    for idea in created_ideas:
        await db.refresh(idea)

    # Perform clustering if we have enough ideas
    all_ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == data.session_id)
    )
    all_ideas = all_ideas_result.scalars().all()

    if len(all_ideas) >= 10:
        # Get all embeddings
        all_embeddings_array = np.array([np.array(idea.embedding) for idea in all_ideas])

        # Perform clustering
        clustering_result = clustering_service.fit_transform(all_embeddings_array)

        # Update coordinates and cluster assignments
        for i, idea in enumerate(all_ideas):
            idea.x = float(clustering_result.coordinates[i, 0])
            idea.y = float(clustering_result.coordinates[i, 1])
            idea.cluster_id = int(clustering_result.cluster_labels[i])

        await db.commit()

        # Delete all existing clusters for this session to avoid leftover clusters
        await db.execute(
            delete(Cluster).where(Cluster.session_id == data.session_id)
        )
        await db.commit()

        # Create/update clusters with simple labels
        cluster_ideas: dict[int, list[Idea]] = {}
        for idea in all_ideas:
            if idea.cluster_id is not None:
                if idea.cluster_id not in cluster_ideas:
                    cluster_ideas[idea.cluster_id] = []
                cluster_ideas[idea.cluster_id].append(idea)

        for cluster_id, cluster_idea_list in cluster_ideas.items():
            # Simple label without LLM
            label = generate_simple_label(cluster_id)

            # Calculate convex hull
            cluster_coords = np.array(
                [[idea.x, idea.y] for idea in cluster_idea_list]
            )
            convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

            # Calculate average novelty
            avg_novelty = (
                sum(idea.novelty_score for idea in cluster_idea_list)
                / len(cluster_idea_list)
            )

            # Sample ideas
            sample_size = min(10, len(cluster_idea_list))
            sampled_ideas = np.random.choice(
                cluster_idea_list, sample_size, replace=False
            )

            # Create or update cluster
            cluster_result = await db.execute(
                select(Cluster).where(
                    Cluster.session_id == data.session_id, Cluster.id == cluster_id
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
                    session_id=data.session_id,
                    label=label,
                    convex_hull_points=convex_hull_points,
                    sample_idea_ids=[str(idea.id) for idea in sampled_ideas],
                    idea_count=len(cluster_idea_list),
                    avg_novelty_score=avg_novelty,
                )
                db.add(cluster)

        await db.commit()

    return {
        "message": f"Created {len(created_ideas)} ideas",
        "created_count": len(created_ideas),
        "total_ideas": len(all_ideas),
        "clustered": len(all_ideas) >= 10,
    }


class QuickSessionCreate(BaseModel):
    """Quick session creation."""

    title: str
    description: str | None = None
    idea_count: int = 100


@router.post("/quick-session", status_code=status.HTTP_201_CREATED)
async def create_quick_session(
    data: QuickSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a session and populate it with ideas quickly (no LLM calls).

    This endpoint creates a session and immediately populates it with
    the specified number of random ideas from a predefined list.
    """
    # Sample ideas for quick testing
    SAMPLE_IDEAS = [
        "ダークモードを追加する",
        "アニメーションでフィードバックを強化",
        "ユーザーインターフェースを簡素化",
        "モバイル対応の改善",
        "アクセシビリティ機能を追加",
        "カラーテーマのカスタマイズ",
        "ユーザーオンボーディングの改善",
        "ショートカットキーの追加",
        "レスポンシブデザインの最適化",
        "ローディングアニメーションの改善",
        "ページ読み込み速度の最適化",
        "キャッシュ機能の実装",
        "データベースクエリの最適化",
        "画像の遅延読み込み",
        "コード分割の導入",
        "CDNの活用",
        "バンドルサイズの削減",
        "メモリ使用量の最適化",
        "並列処理の実装",
        "インデックスの最適化",
        "リアルタイムチャット機能",
        "通知システムの実装",
        "検索機能の強化",
        "フィルター機能の追加",
        "エクスポート機能",
        "インポート機能",
        "バッチ処理機能",
        "自動保存機能",
        "バージョン管理",
        "コラボレーション機能",
        "二段階認証の導入",
        "暗号化の強化",
        "セッション管理の改善",
        "CSRF対策の実装",
        "XSS対策の強化",
        "レート制限の導入",
        "監査ログの実装",
        "権限管理の強化",
        "セキュリティスキャンの自動化",
        "脆弱性診断の定期実施",
        "ユーザー行動分析",
        "A/Bテスト機能",
        "ダッシュボードの実装",
        "レポート生成機能",
        "カスタムメトリクス",
        "リアルタイム分析",
        "ヒートマップ機能",
        "ファネル分析",
        "コホート分析",
        "セグメンテーション機能",
        "E2Eテストの拡充",
        "ユニットテストカバレッジ向上",
        "統合テストの自動化",
        "パフォーマンステスト",
        "セキュリティテスト",
        "アクセシビリティテスト",
        "クロスブラウザテスト",
        "負荷テスト",
        "回帰テストの自動化",
        "テストデータ生成の自動化",
        "CI/CDパイプラインの改善",
        "デプロイの自動化",
        "モニタリング強化",
        "ログ集約システム",
        "アラート設定の最適化",
        "バックアップ自動化",
        "災害復旧計画",
        "コンテナ化の推進",
        "オーケストレーション",
        "インフラのコード化",
        "APIドキュメントの充実",
        "ユーザーガイドの作成",
        "チュートリアルの追加",
        "FAQ作成",
        "技術仕様書の更新",
        "コードコメントの改善",
        "アーキテクチャ図の作成",
        "データフロー図の作成",
        "ER図の作成",
        "シーケンス図の作成",
        "Slack連携",
        "Google Calendar連携",
        "GitHub連携",
        "Jira連携",
        "Webhookサポート",
        "REST API拡張",
        "GraphQL APIの実装",
        "SSO統合",
        "OAuth2.0対応",
        "サードパーティ連携",
        "モバイルアプリ開発",
        "プッシュ通知",
        "オフライン機能",
        "位置情報機能",
        "カメラ統合",
        "生体認証",
        "ウィジェット対応",
        "アプリ内課金",
        "ディープリンク",
        "クロスプラットフォーム対応",
    ]

    # Create session
    session = Session(
        title=data.title,
        description=data.description or "デバッグ用クイックセッション",
        duration=3600,
        status="active",
        accepting_ideas=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Create user
    user = User(
        user_id=str(uuid.uuid4()),
        session_id=session.id,
        name="デバッグユーザー",
        total_score=0.0,
        idea_count=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate ideas
    ideas_to_create = []
    for _ in range(min(data.idea_count, len(SAMPLE_IDEAS))):
        ideas_to_create.append(np.random.choice(SAMPLE_IDEAS))

    # Use bulk creation
    bulk_data = BulkIdeaCreate(
        session_id=session.id, user_id=user.user_id, ideas=ideas_to_create
    )

    result = await create_bulk_ideas(bulk_data, db)

    return {
        "session_id": session.id,
        "session_title": session.title,
        "user_id": user.user_id,
        "access_url": f"http://localhost:5173/session/{session.id}/join",
        **result,
    }


class ForceClusterRequest(BaseModel):
    """Force clustering request."""

    session_id: str
    use_llm_labels: bool = False  # If True, use LLM to generate cluster labels
    fixed_cluster_count: int | None = None  # If set, use fixed number of clusters


@router.post("/force-cluster", status_code=status.HTTP_200_OK)
async def force_cluster(
    data: ForceClusterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Force clustering on an existing session.

    This endpoint re-computes clustering, coordinates, and cluster metadata
    for all ideas in a session. Useful for fixing sessions that failed during
    clustering or to update clustering after adding many ideas.
    """
    # Log received parameters
    logger.info(f"[FORCE-CLUSTER] Received request: session_id={data.session_id}, use_llm_labels={data.use_llm_labels}, fixed_cluster_count={data.fixed_cluster_count}")

    # Check if clustering is already in progress for this session
    if _clustering_locks.get(data.session_id, False):
        logger.warning(f"[FORCE-CLUSTER] Clustering already in progress for session {data.session_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="クラスタリングが実行中です。完了するまでお待ちください。"
        )

    # Acquire lock
    _clustering_locks[data.session_id] = True
    logger.info(f"[FORCE-CLUSTER] Acquired clustering lock for session {data.session_id}")

    # Notify clients that clustering has started
    await manager.send_clustering_started(data.session_id)

    try:
        # Verify session
        session_result = await db.execute(
            select(Session).where(Session.id == data.session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Update fixed_cluster_count in session (set to None if not provided to enable auto mode)
        session.fixed_cluster_count = data.fixed_cluster_count
        await db.commit()
        await db.refresh(session)

        # Get all ideas
        ideas_result = await db.execute(
            select(Idea).where(Idea.session_id == data.session_id)
        )
        all_ideas = ideas_result.scalars().all()

        if len(all_ideas) < 10:
            return {
                "message": "Not enough ideas for clustering (minimum 10)",
                "idea_count": len(all_ideas),
                "clustered": False,
            }

        # Clear cached clustering service to force re-fitting UMAP model
        clear_clustering_service(data.session_id)

        # Get fresh clustering service for this session with fixed_cluster_count
        clustering_service = get_clustering_service(
            data.session_id,
            fixed_cluster_count=session.fixed_cluster_count
        )

        # Get all embeddings
        all_embeddings_array = np.array([np.array(idea.embedding) for idea in all_ideas])

        # Perform clustering (this will fit a new UMAP model)
        clustering_result = clustering_service.fit_transform(all_embeddings_array)

        # Update coordinates and cluster assignments
        await update_idea_coordinates(
            db,
            all_ideas,
            clustering_result.coordinates,
            clustering_result.cluster_labels
        )

        # Delete all existing clusters for this session to avoid leftover clusters
        await delete_existing_clusters(db, data.session_id)

        # Group ideas by cluster
        cluster_ideas = await group_ideas_by_cluster(all_ideas)

        # Initialize LLM service if needed
        llm_service = None
        if data.use_llm_labels:
            try:
                llm_service = get_llm_service()
                logger.info(f"[FORCE-CLUSTER] LLM service initialized successfully")
            except Exception as e:
                logger.error(f"[FORCE-CLUSTER] Failed to initialize LLM service: {e}")
                llm_service = None

        # Generate labels in parallel
        label_results = await generate_cluster_labels_parallel(
            cluster_ideas,
            session,
            llm_service,
            data.use_llm_labels
        )

        # Create/update clusters with generated labels
        await create_or_update_clusters(
            db,
            data.session_id,
            cluster_ideas,
            label_results,
            clustering_service
        )

        # Get updated cluster labels from database
        clusters_result = await db.execute(
            select(Cluster).where(Cluster.session_id == data.session_id)
        )
        clusters = clusters_result.scalars().all()
        cluster_labels = {cluster.id: cluster.label for cluster in clusters}

        # Broadcast cluster recalculation to all connected clients
        logger.info(f"[FORCE-CLUSTER] Broadcasting cluster recalculation event to session {data.session_id}")
        await manager.send_clusters_recalculated(data.session_id)

        return {
            "message": "Clustering completed",
            "idea_count": len(all_ideas),
            "cluster_count": len(cluster_ideas),
            "clustered": True,
            "clusters": build_cluster_response(cluster_ideas, cluster_labels),
        }
    finally:
        # Always release the lock
        _clustering_locks[data.session_id] = False
        logger.info(f"[FORCE-CLUSTER] Released clustering lock for session {data.session_id}")
        # Notify clients that clustering has completed
        await manager.send_clustering_completed(data.session_id)


@router.post("/create-test-session", status_code=status.HTTP_201_CREATED)
async def create_test_session(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a test session with 300 diverse random ideas.

    This endpoint creates:
    - A test session with unlimited duration
    - 10 test users
    - 100 random ideas distributed among the users
    - Automatically runs clustering

    Returns the created session and statistics.
    """
    logger.info("[TEST-SESSION] Creating test session...")

    # Create test session
    session_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = Session(
        id=session_id,
        title=f"テストセッション {timestamp}",
        description="自動生成されたテストセッション（300個の多様なアイデア）",
        status="active",
        accepting_ideas=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(f"[TEST-SESSION] Created session: {session_id}")

    # Create test users (10 users)
    user_names = [
        "テストユーザー1", "テストユーザー2", "テストユーザー3", "テストユーザー4", "テストユーザー5",
        "テストユーザー6", "テストユーザー7", "テストユーザー8", "テストユーザー9", "テストユーザー10"
    ]
    user_ids = []

    for name in user_names:
        user_id = str(uuid.uuid4())
        user = User(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            name=name,
        )
        db.add(user)
        user_ids.append((user.id, user_id, name))

    await db.commit()
    logger.info(f"[TEST-SESSION] Created {len(user_ids)} test users")

    # Generate 300 ideas from templates with diverse variations
    ideas_to_create = []

    # Diverse variation strategies (expanded)
    suffix_variations = [
        "を実施する", "を強化する", "を見直す", "を最適化する", "を改良する",
        "を推進する", "を検討する", "を試行する", "を導入する", "を評価する",
        "の仕組みを作る", "のガイドラインを策定する", "の計画を立てる",
        "を本格化する", "を加速する", "を拡大する", "を深化する", "を展開する",
        "に着手する", "を実現する", "を完成させる", "を刷新する", "を徹底する"
    ]

    prefix_variations = [
        "まずは", "積極的に", "段階的に", "継続的に", "効果的に",
        "戦略的に", "組織的に", "計画的に", "柔軟に", "迅速に",
        "思い切って", "大胆に", "慎重に", "丁寧に", "着実に",
        "早急に", "優先的に", "集中的に", "全力で", "本気で"
    ]

    context_additions = [
        "（チーム全体で）", "（長期的に）", "（短期集中で）",
        "（優先度を上げて）", "（コストを抑えて）", "（品質重視で）",
        "（段階的に）", "（全社的に）", "（部門横断で）",
        "（ユーザー目線で）", "（データドリブンで）", "（アジャイルに）",
        "（スピード重視で）", "（安全第一で）", "（効率化して）",
        "（実験的に）", "（小さく始めて）", "（大規模に）"
    ]

    intensity_variations = [
        "もっと", "さらに", "もう少し", "大幅に", "抜本的に",
        "根本的に", "徹底的に", "一層", "より一層", "格段に"
    ]

    time_variations = [
        "今すぐ", "今年中に", "来月から", "次の四半期に", "年度内に",
        "できるだけ早く", "タイミングを見て", "適切な時期に"
    ]

    for i in range(300):
        # Select base template
        base_text = random.choice(STARTER_IDEA_TEMPLATES)

        # Apply random variations (80% chance)
        if random.random() > 0.2:
            variation_type = random.randint(1, 8)

            if variation_type == 1:
                # Add suffix only
                base_text += random.choice(suffix_variations)
            elif variation_type == 2:
                # Add prefix only
                base_text = random.choice(prefix_variations) + base_text
            elif variation_type == 3:
                # Add context only
                base_text = base_text + random.choice(context_additions)
            elif variation_type == 4:
                # Combine prefix and suffix
                base_text = random.choice(prefix_variations) + base_text + random.choice(suffix_variations)
            elif variation_type == 5:
                # Combine suffix and context
                base_text = base_text + random.choice(suffix_variations) + random.choice(context_additions)
            elif variation_type == 6:
                # Add intensity and suffix
                base_text = random.choice(intensity_variations) + base_text + random.choice(suffix_variations)
            elif variation_type == 7:
                # Add time and prefix
                base_text = random.choice(time_variations) + random.choice(prefix_variations) + base_text
            else:
                # Combine all three (prefix, suffix, context)
                base_text = random.choice(prefix_variations) + base_text + random.choice(suffix_variations) + random.choice(context_additions)

        ideas_to_create.append(base_text)

    logger.info(f"[TEST-SESSION] Generated {len(ideas_to_create)} idea texts")

    # Create ideas using bulk logic
    embedding_service = EmbeddingService()
    novelty_scorer = NoveltyScorer()

    # Distribute ideas among users
    created_ideas = []
    for i, idea_text in enumerate(ideas_to_create):
        # Round-robin distribution among users
        user_db_id, user_id, user_name = user_ids[i % len(user_ids)]

        # Generate embedding
        embedding = await embedding_service.embed(idea_text)

        # Calculate novelty score and find closest idea
        existing_embeddings = [idea.embedding for idea in created_ideas]
        novelty_score = novelty_scorer.calculate_score(embedding, existing_embeddings)

        # Find closest idea and apply penalty if same user
        closest_idea_id = None
        if len(created_ideas) > 0:
            similarities = cosine_similarity(
                embedding.reshape(1, -1),
                np.array(existing_embeddings)
            )[0]
            closest_idx = np.argmax(similarities)
            closest_idea = created_ideas[closest_idx]
            closest_idea_id = str(closest_idea.id)

            # Apply 0.5x penalty if closest idea is from the same user
            if closest_idea.user_id == user_id:
                novelty_score *= 0.5

        # Create idea
        idea = Idea(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,  # Use user_id (UUID), not user_db_id (PK)
            raw_text=idea_text,
            formatted_text=idea_text,  # Skip LLM formatting for test data
            embedding=embedding.tolist(),
            x=0.0,  # Will be set by clustering
            y=0.0,  # Will be set by clustering
            novelty_score=novelty_score,
            closest_idea_id=closest_idea_id,
        )

        db.add(idea)
        created_ideas.append(idea)

    await db.commit()
    logger.info(f"[TEST-SESSION] Created {len(created_ideas)} ideas")

    # Update user scores
    for user_db_id, user_id, user_name in user_ids:
        user_ideas = [idea for idea in created_ideas if idea.user_id == user_id]  # Compare with user_id (UUID)
        total_score = sum(idea.novelty_score for idea in user_ideas)
        idea_count = len(user_ideas)

        user_result = await db.execute(
            select(User).where(User.id == user_db_id)
        )
        user = user_result.scalar_one()
        user.total_score = total_score
        user.idea_count = idea_count

    await db.commit()
    logger.info("[TEST-SESSION] Updated user scores")

    # Run clustering with LLM labels
    logger.info("[TEST-SESSION] Running clustering with LLM labels...")

    # Get all ideas for clustering
    ideas_result = await db.execute(
        select(Idea).where(Idea.session_id == session_id)
    )
    all_ideas = ideas_result.scalars().all()

    if len(all_ideas) >= 10:  # Need at least 10 ideas for clustering
        clustering_service = get_clustering_service(session_id)
        embeddings = np.array([idea.embedding for idea in all_ideas])

        # Perform clustering with UMAP + k-means
        clustering_result = clustering_service.fit_transform(embeddings)

        # Update idea coordinates and cluster assignments
        for i, idea in enumerate(all_ideas):
            idea.x = float(clustering_result.coordinates[i, 0])
            idea.y = float(clustering_result.coordinates[i, 1])
            idea.cluster_id = int(clustering_result.cluster_labels[i])

        await db.commit()

        # Create cluster metadata
        cluster_ideas = {}
        for idea in all_ideas:
            if idea.cluster_id is not None:
                if idea.cluster_id not in cluster_ideas:
                    cluster_ideas[idea.cluster_id] = []
                cluster_ideas[idea.cluster_id].append(idea)

        # Initialize LLM service for label generation
        try:
            llm_service = get_llm_service()
            logger.info("[TEST-SESSION] LLM service initialized for cluster labeling")
        except Exception as e:
            logger.error(f"[TEST-SESSION] Failed to initialize LLM service: {e}")
            llm_service = None

        # Create clusters with LLM-generated labels
        for cluster_id, cluster_idea_list in cluster_ideas.items():
            cluster_coords = np.array(
                [[idea.x, idea.y] for idea in cluster_idea_list]
            )
            convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

            avg_novelty = (
                sum(idea.novelty_score for idea in cluster_idea_list)
                / len(cluster_idea_list)
            )

            sampled_ideas = random.sample(
                cluster_idea_list, min(10, len(cluster_idea_list))
            )

            # Generate label with LLM
            if llm_service:
                try:
                    sample_texts = [idea.formatted_text for idea in sampled_ideas]
                    label = await llm_service.summarize_cluster(
                        sample_texts,
                        session_context=session.description
                    )
                    logger.info(f"[TEST-SESSION] Generated LLM label for cluster {cluster_id}: {label}")
                except Exception as e:
                    logger.error(f"[TEST-SESSION] Failed to generate LLM label for cluster {cluster_id}: {e}")
                    label = generate_simple_label(cluster_id)  # Fallback to simple label
            else:
                label = generate_simple_label(cluster_id)  # Fallback if LLM not available

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
        logger.info(f"[TEST-SESSION] Created {len(cluster_ideas)} clusters with LLM labels")

    # Create random votes for each user (100 votes per user)
    logger.info("[TEST-SESSION] Creating random votes...")

    # Get all idea IDs
    all_idea_ids = [idea.id for idea in created_ideas]
    vote_count = 0

    for user_db_id, user_id, user_name in user_ids:
        # Each user votes on 100 random ideas
        num_votes = min(100, len(all_idea_ids))  # Don't exceed total number of ideas
        voted_idea_ids = random.sample(all_idea_ids, num_votes)

        for idea_id in voted_idea_ids:
            vote = Vote(
                id=str(uuid.uuid4()),
                idea_id=idea_id,
                user_id=user_db_id,  # Use the internal user DB ID
            )
            db.add(vote)
            vote_count += 1

    await db.commit()
    logger.info(f"[TEST-SESSION] Created {vote_count} random votes ({num_votes} per user)")

    return {
        "message": "Test session created successfully",
        "session_id": session_id,
        "session_title": session.title,
        "user_count": len(user_ids),
        "idea_count": len(created_ideas),
        "cluster_count": len(cluster_ideas) if len(all_ideas) >= 3 else 0,
        "vote_count": vote_count,
    }
