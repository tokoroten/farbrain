"""
Create a demo session with 100 ideas for testing clustering visualization.

Run this script to create a session populated with diverse ideas that will
form multiple clusters for testing the visualization.
"""

import asyncio
import random
from pathlib import Path
from uuid import uuid4

import numpy as np
from dotenv import load_dotenv
from sqlalchemy import select

# Add backend directory to Python path
import sys
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir.parent))

# Load environment variables from .env file
env_path = backend_dir / ".env"
load_dotenv(env_path)

from backend.app.db.base import AsyncSessionLocal
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.idea import Idea
from backend.app.services.embedding import EmbeddingService
from backend.app.services.llm import get_llm_service
from backend.app.services.clustering import ClusteringService
from backend.app.services.scoring import NoveltyScorer

# Sample ideas across different topics to create diverse clusters
SAMPLE_IDEAS = [
    # UI/UX improvements
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

    # Performance
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

    # Features
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

    # Security
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

    # Analytics
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

    # Testing
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

    # DevOps
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

    # Documentation
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

    # Integration
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

    # Mobile
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


async def create_demo_session():
    """Create a demo session with 100 ideas."""
    print("Creating demo session...")

    # Initialize services
    embedding_service = EmbeddingService()
    llm_service = get_llm_service()
    clustering_service = ClusteringService()
    novelty_scorer = NoveltyScorer()

    async with AsyncSessionLocal() as db:
        # Create session
        session = Session(
            title="デモセッション - クラスタリングテスト",
            description="クラスタ表示機能をテストするための100個のアイディアを含むセッション",
            duration=3600,
            status="active",
            accepting_ideas=True,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        print(f"Created session: {session.id}")

        # Create demo user
        user = User(
            user_id=str(uuid4()),
            session_id=session.id,
            name="デモユーザー",
            total_score=0.0,
            idea_count=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created user: {user.name}")

        # Create 100 ideas
        ideas_to_create = []
        all_embeddings = []

        print("Generating ideas...")
        for i in range(100):
            # Pick a random idea from samples
            raw_text = random.choice(SAMPLE_IDEAS)

            # Format with LLM
            formatted_text = await llm_service.format_idea(
                raw_text,
                session_context=session.description
            )

            # Generate embedding
            embedding = await embedding_service.embed(formatted_text)
            embedding_list = embedding.tolist()
            all_embeddings.append(embedding)

            # Initial random coordinates (will be updated after clustering)
            x = float(np.random.uniform(-10, 10))
            y = float(np.random.uniform(-10, 10))

            # Calculate novelty score and find closest idea
            closest_idea_id = None
            if i == 0:
                novelty_score = 100.0
            else:
                existing_embeddings = np.array(all_embeddings[:-1])
                novelty_score = novelty_scorer.calculate_score(
                    embedding.reshape(1, -1),
                    existing_embeddings
                )

                # Find closest idea (highest similarity)
                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity(
                    embedding.reshape(1, -1),
                    existing_embeddings
                )[0]
                closest_idx = np.argmax(similarities)
                closest_idea_id = str(ideas_to_create[closest_idx].id)

            idea = Idea(
                session_id=session.id,
                user_id=user.user_id,
                raw_text=raw_text,
                formatted_text=formatted_text,
                embedding=embedding_list,
                x=x,
                y=y,
                cluster_id=None,
                novelty_score=novelty_score,
                closest_idea_id=closest_idea_id,
            )

            ideas_to_create.append(idea)

            if (i + 1) % 10 == 0:
                print(f"  Generated {i + 1}/100 ideas...")

        # Add all ideas to database
        print("Saving ideas to database...")
        for idea in ideas_to_create:
            db.add(idea)

        # Update user stats
        user.idea_count = 100
        user.total_score = sum(idea.novelty_score for idea in ideas_to_create)

        await db.commit()
        print(f"Saved {len(ideas_to_create)} ideas")

        # Perform clustering on all ideas
        print("Performing clustering...")
        all_embeddings_array = np.array(all_embeddings)
        clustering_result = clustering_service.fit_transform(all_embeddings_array)

        # Update ideas with cluster assignments and coordinates
        print("Updating coordinates and clusters...")
        for i, idea in enumerate(ideas_to_create):
            idea.x = float(clustering_result.coordinates[i, 0])
            idea.y = float(clustering_result.coordinates[i, 1])
            idea.cluster_id = int(clustering_result.cluster_labels[i])

        await db.commit()

        # Group ideas by cluster for labeling
        from backend.app.models.cluster import Cluster

        print("Generating cluster labels...")
        cluster_ideas: dict[int, list[Idea]] = {}
        for idea in ideas_to_create:
            if idea.cluster_id is not None:
                if idea.cluster_id not in cluster_ideas:
                    cluster_ideas[idea.cluster_id] = []
                cluster_ideas[idea.cluster_id].append(idea)

        # Create cluster labels
        for cluster_id, cluster_idea_list in cluster_ideas.items():
            # Sample up to 10 ideas
            sample_size = min(10, len(cluster_idea_list))
            sampled_ideas = random.sample(cluster_idea_list, sample_size)
            sample_texts = [idea.formatted_text for idea in sampled_ideas]

            # Generate label
            label = await llm_service.summarize_cluster(
                sample_texts,
                session_context=session.description
            )

            # Calculate convex hull
            cluster_coords = np.array([[idea.x, idea.y] for idea in cluster_idea_list])
            convex_hull_points = clustering_service.compute_convex_hull(cluster_coords)

            # Calculate average novelty
            avg_novelty = sum(idea.novelty_score for idea in cluster_idea_list) / len(cluster_idea_list)

            # Create cluster
            cluster = Cluster(
                id=cluster_id,
                session_id=session.id,
                label=label,
                convex_hull_points=convex_hull_points,
                sample_idea_ids=[str(idea.id) for idea in sampled_ideas],
                idea_count=len(cluster_idea_list),
                avg_novelty_score=avg_novelty,
            )
            db.add(cluster)

            print(f"  Cluster {cluster_id}: {label} ({len(cluster_idea_list)} ideas)")

        await db.commit()

        print("\n[OK] Demo session created successfully!")
        print(f"Session ID: {session.id}")
        print(f"Total ideas: {len(ideas_to_create)}")
        print(f"Total clusters: {len(cluster_ideas)}")
        print(f"\nAccess the session at: http://localhost:5173/session/{session.id}/join")


if __name__ == "__main__":
    asyncio.run(create_demo_session())
