# FarBrain アーキテクチャ設計

## システム全体像

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Browser                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         React Frontend (TypeScript)                    │ │
│  │  - UI Components                                        │ │
│  │  - D3.js Visualization                                  │ │
│  │  - WebSocket Client                                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP / WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  REST API Routers                                       │ │
│  │  - Sessions  - Ideas  - Users  - Visualization         │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  WebSocket Manager (Real-time sync)                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Services Layer                                         │ │
│  │  - LLM Service (OpenAI/Ollama - configurable)         │ │
│  │  - Vectorization (Sentence Transformers)              │ │
│  │  - Clustering (UMAP + k-means)                         │ │
│  │  - Scoring (Anomaly Detection)                         │ │
│  │  - Visualization (Convex Hull)                         │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Database (SQLAlchemy ORM)                             │ │
│  │  - Session  - User  - Idea  - Cluster                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                         SQLite
                            │
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  - OpenAI API (GPT-4) - optional, configurable              │
│  - Sentence Transformers (local embeddings)                 │
└─────────────────────────────────────────────────────────────┘
```

## データモデル

### Session (セッション)
```python
Session:
  - id: UUID
  - title: str
  - start_time: datetime
  - duration: int (seconds, default: 7200)
  - status: enum ['active', 'ended']
  - created_at: datetime
```

### User (ユーザー)
```python
User:
  - id: UUID
  - session_id: UUID (FK)
  - name: str
  - total_score: float
  - joined_at: datetime
```

### Idea (アイディア)
```python
Idea:
  - id: UUID
  - session_id: UUID (FK)
  - user_id: UUID (FK)
  - raw_text: str (生の意見)
  - formatted_text: str (LLM成形後)
  - embedding: List[float] (768次元 - paraphrase-multilingual-mpnet-base-v2 default)
  - x: float (UMAP 2D x座標)
  - y: float (UMAP 2D y座標)
  - cluster_id: int
  - novelty_score: float
  - timestamp: datetime
```

### Cluster (クラスタ)
```python
Cluster:
  - id: int
  - session_id: UUID (FK)
  - label: str (LLM生成)
  - convex_hull_points: JSON (凸包の頂点座標)
  - sample_idea_ids: List[UUID] (ラベル生成に使った標本)
  - updated_at: datetime
```

## データフロー詳細

### 1. アイディア投稿フロー
```
User Input (生の意見)
    ↓
POST /api/ideas
    ↓
LLM Service: 意見成形 (OpenAI/Ollama - .env設定)
    ↓
Vectorization Service: Sentence Transformers (→ 768次元ベクトル)
    ↓
Database: Idea保存 (embedding含む)
    ↓
Clustering Service:
    - 全アイディアのembeddingを取得
    - UMAP: 768次元 → 2次元
    - k-means: クラスタ割り当て
    - 凸包計算
    ↓
Scoring Service:
    - 異常検知アルゴリズム (Isolation Forest / LOF)
    - 既存アイディア集合との距離計算
    - novelty_score算出
    ↓
Database: Idea更新 (x, y, cluster_id, novelty_score)
Database: User.total_score更新
    ↓
WebSocket Broadcast:
    - 新アイディア情報
    - 更新された可視化データ
    - 更新されたスコアボード
```

### 2. クラスタラベル生成フロー
```
Trigger: 新アイディア追加 or 定期実行
    ↓
各クラスタについて:
    - クラスタ内のアイディアを取得
    - ランダムサンプリング (3-5件)
    - サンプルのformatted_textを結合
    ↓
LLM Service: クラスタ要約
    - プロンプト: "以下のアイディアに共通するテーマを1-3語で要約してください"
    - 入力: サンプルアイディア
    - 出力: クラスタラベル
    ↓
Database: Cluster更新 (label, sample_idea_ids)
    ↓
WebSocket Broadcast: クラスタラベル更新
```

### 3. リアルタイム同期フロー
```
WebSocket Connection確立
    ↓
Client → Server: {"type": "join_session", "session_id": "...", "user_name": "..."}
    ↓
Server: ユーザー登録、既存データ送信
    ↓
Server → Client: 初期データ (全アイディア、クラスタ、スコアボード)
    ↓
[アイディア投稿時]
    ↓
Server → All Clients: {"type": "new_idea", "data": {...}}
Server → All Clients: {"type": "visualization_update", "data": {...}}
Server → All Clients: {"type": "scoreboard_update", "data": {...}}
```

## 機械学習パイプライン

### Sentence Transformersによるベクトル化
```python
from sentence_transformers import SentenceTransformer

# モデル読み込み (.env で指定可能)
model_name = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
model = SentenceTransformer(model_name)

# テキストをベクトル化 (768次元)
embedding = model.encode(formatted_text, convert_to_numpy=True)
```

**推奨モデル:**
- `paraphrase-multilingual-mpnet-base-v2`: 高精度・多言語対応、768次元 (デフォルト)
- `all-mpnet-base-v2`: 高精度・英語のみ、768次元
- `intfloat/multilingual-e5-large`: 最高精度・多言語、1024次元
- `all-MiniLM-L6-v2`: 軽量・高速、384次元 (低リソース環境向け)

### UMAP次元圧縮
```python
import umap

reducer = umap.UMAP(
    n_components=2,
    n_neighbors=15,
    min_dist=0.1,
    metric='cosine',
    random_state=42
)

embeddings_2d = reducer.fit_transform(embeddings_768d)
```

### k-meansクラスタリング
```python
from sklearn.cluster import KMeans

# クラスタ数の決定: エルボー法またはシルエットスコア
n_clusters = min(max(3, len(ideas) // 10), 10)

kmeans = KMeans(n_clusters=n_clusters, random_state=42)
cluster_labels = kmeans.fit_predict(embeddings_2d)
```

### 異常検知スコアリング
```python
from sklearn.ensemble import IsolationForest

# 新規性スコア = 既存集合からの乖離度
iso_forest = IsolationForest(contamination=0.1, random_state=42)
iso_forest.fit(existing_embeddings)

# 新アイディアの異常度スコア (-1 to 1, 高いほど異常=新規)
novelty_score = iso_forest.decision_function([new_embedding])[0]

# 正規化: 0-100点
normalized_score = (novelty_score + 0.5) * 100
```

### 凸包計算
```python
from scipy.spatial import ConvexHull

points = embeddings_2d[cluster_labels == cluster_id]
hull = ConvexHull(points)
hull_points = points[hull.vertices].tolist()
```

## API設計原則

### RESTful Endpoints
- **GET**: データ取得 (冪等)
- **POST**: リソース作成
- **PUT/PATCH**: リソース更新
- **DELETE**: リソース削除

### WebSocket Events
- **join_session**: セッション参加
- **new_idea**: 新アイディア追加通知
- **visualization_update**: 可視化データ更新
- **scoreboard_update**: スコアボード更新
- **session_ended**: セッション終了通知

## スケーラビリティ考慮事項

### 現在の実装 (MVP)
- SQLite (単一ファイルDB)
- インメモリキャッシュ
- 単一サーバーインスタンス

### 将来的な拡張
- PostgreSQL (複数セッション対応)
- Redis (WebSocket状態管理、キャッシュ)
- 水平スケーリング (ロードバランサー + 複数バックエンドインスタンス)
- 非同期タスクキュー (Celery) for 重い計算処理

## セキュリティ

### 現在の実装
- CORS設定
- 環境変数によるAPIキー管理
- セッションIDによる簡易認証

### 将来的な強化
- JWT認証
- レート制限
- 入力バリデーション強化
- HTTPS必須化

## パフォーマンス最適化

### キャッシュ戦略
- クラスタリング結果のキャッシュ (5秒TTL)
- UMAP計算結果のキャッシュ
- LLMレスポンスのキャッシュ (同一入力)

### 計算最適化
- バッチ処理: 複数アイディアをまとめてembedding取得
- 差分更新: 全体再計算ではなく増分更新
- 非同期処理: 重い計算をバックグラウンドで実行
