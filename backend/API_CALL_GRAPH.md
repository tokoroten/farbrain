# FarBrain API コールグラフ

## 1. アイディア投稿フロー (POST /api/ideas)

```
POST /api/ideas
  ↓
┌─────────────────────────────────────────────────────────────┐
│ create_idea(idea_data, db)                                  │
│ backend/app/api/ideas.py:34                                 │
└─────────────────────────────────────────────────────────────┘
  ↓
  ├─ セッション検証 (Line 49-70)
  │   └─ SELECT Session WHERE id = session_id
  │
  ├─ ユーザー検証 (Line 73-85)
  │   └─ SELECT User WHERE session_id & user_id
  │
  ├─ 既存アイディア取得 (Line 87-92)
  │   └─ SELECT Idea WHERE session_id
  │   └─ n_existing = len(existing_ideas)
  │
  ├─ ClusteringService取得 (Line 95-98)
  │   └─ get_clustering_service(session_id, fixed_cluster_count)
  │       backend/app/services/clustering.py:351
  │       ↓
  │       ├─ session_id が _clustering_services にある？
  │       │   YES → キャッシュから返す (umap_model保持)
  │       │   NO  → 新規作成 (umap_model=None)
  │       │           └─ ClusteringService.__init__()
  │       │               └─ self.umap_model = None
  │       │               └─ self.kmeans_model = None
  │       └─ return _clustering_services[session_id]
  │
  ├─ LLMフォーマット (Line 101-108)
  │   └─ llm_service.format_idea(raw_text, custom_prompt, session_context)
  │       backend/app/services/llm.py:210
  │       └─ provider.generate(prompt, system_prompt)
  │
  ├─ エンベディング生成 (Line 111-112)
  │   └─ embedding_service.embed(formatted_text)
  │       backend/app/services/embedding.py:133
  │       ↓
  │       ├─ _preprocess_text(text)  # 前処理（strip、改行除去）
  │       ├─ embed_sync(text, normalize=True)
  │       │   └─ self.model.encode(text, normalize_embeddings=True)
  │       │       └─ SentenceTransformer.encode()
  │       └─ return np.ndarray (shape: (768,))
  │
  ├─ 新規性スコア計算 (Line 115-122)
  │   └─ novelty_scorer.calculate_score(embedding, existing_embeddings)
  │       backend/app/services/scoring.py:50
  │       └─ IsolationForest.fit_predict()
  │
  ├─ 座標割り当て (Line 125-182) ⭐重要⭐
  │   │
  │   ├─ CASE 1: n_existing < 9 (1〜9個目)
  │   │   └─ ランダム座標生成
  │   │       x = random(-10, 10)
  │   │       y = random(-10, 10)
  │   │       cluster_id = None
  │   │
  │   ├─ CASE 2: n_existing == 9 (10個目)
  │   │   └─ 初回UMAP+クラスタリング
  │   │       all_embeddings = [existing_embeddings + new_embedding]
  │   │       ↓
  │   │       clustering_result = clustering_service.fit_transform(all_embeddings)
  │   │       backend/app/services/clustering.py:123
  │   │       ↓
  │   │       ├─ self.umap_model = umap.UMAP(n_neighbors=50, min_dist=0.3, ...)
  │   │       ├─ coordinates = self.umap_model.fit_transform(embeddings)
  │   │       ├─ self.kmeans_model = KMeans(n_clusters=...)
  │   │       ├─ cluster_labels = self.kmeans_model.fit_predict(coordinates)
  │   │       └─ return ClusteringResult(coordinates, cluster_labels, ...)
  │   │       ↓
  │   │       ├─ 新アイディアの座標取得: coordinates[-1]
  │   │       └─ 既存9個のアイディアの座標も更新
  │   │
  │   └─ CASE 3: n_existing >= 10 (11個目以降) ⭐問題発生箇所⭐
  │       ↓
  │       logger.info(f"[IDEA-CREATE] Processing idea #{n_existing + 1}")
  │       logger.info(f"[IDEA-CREATE] UMAP model status: {NONE or EXISTS}")
  │       ↓
  │       ├─ clustering_service.umap_model is None?
  │       │   │
  │       │   YES → 再クラスタリング (Line 151-173)
  │       │   │     ↓
  │       │   │     all_embeddings = [existing + new]
  │       │   │     clustering_result = clustering_service.fit_transform(all_embeddings)
  │       │   │     └─ 全アイディアの座標を再計算
  │       │   │
  │       │   NO → 既存モデル使用 (Line 174-182)
  │       │         ↓
  │       │         x, y = clustering_service.transform(embedding)
  │       │         backend/app/services/clustering.py:198
  │       │         ↓
  │       │         ├─ if self.umap_model is None:
  │       │         │   └─ ⚠️ ランダム座標を返す ⚠️
  │       │         │       return _generate_random_coordinates(1)
  │       │         │
  │       │         └─ coords = self.umap_model.transform(embedding)
  │       │             return (x, y)
  │       │         ↓
  │       │         cluster_id = clustering_service.predict_cluster((x, y))
  │       │
  │       └─ 座標とクラスタIDを取得
  │
  ├─ アイディア作成 (Line 185-196)
  │   └─ idea = Idea(session_id, user_id, raw_text, formatted_text,
  │                   embedding, x, y, cluster_id, novelty_score)
  │   └─ db.add(idea)
  │
  ├─ ユーザースコア更新 (Line 199-201)
  │   └─ user.total_score += novelty_score
  │   └─ user.idea_count += 1
  │
  ├─ データベースコミット (Line 203-205)
  │   └─ await db.commit()
  │
  ├─ WebSocket通知 (Line 208-219)
  │   └─ manager.send_idea_created(session_id, idea_id, ...)
  │       backend/app/websocket/manager.py
  │       └─ broadcast_to_session(session_id, message)
  │
  └─ 定期クラスタリング・ラベル更新 (Line 222-232)
      ├─ new_total % reclustering_interval == 0 (50個ごと)
      │   └─ asyncio.create_task(full_recluster_session(session_id, db))
      │       backend/app/api/ideas.py:252
      │       ↓
      │       ├─ get_clustering_service(session_id, ...)
      │       ├─ clustering_result = clustering_service.fit_transform(all_embeddings)
      │       ├─ 全アイディアの座標・クラスタを更新
      │       └─ update_cluster_labels(session_id, db)
      │
      └─ new_total % clustering_interval == 0 (10個ごと)
          └─ asyncio.create_task(update_cluster_labels(session_id, db))
```

## 2. グローバル変数とキャッシュ

### ClusteringService キャッシュ
```
backend/app/services/clustering.py:348

_clustering_services: dict[str, ClusteringService] = {}
  ↓
  key: session_id (str)
  value: ClusteringService instance
    ├─ umap_model: umap.UMAP | None
    ├─ kmeans_model: KMeans | None
    ├─ n_neighbors: int
    ├─ min_dist: float
    └─ fixed_cluster_count: int | None

重要な特性:
- モジュールレベル変数 → プロセス全体で共有
- バックエンド再起動 → 空辞書にリセット
- 初回get_clustering_service() → 新規作成 (umap_model=None)
- 2回目以降 → キャッシュから取得 (umap_model保持)
```

### EmbeddingService シングルトン
```
backend/app/services/embedding.py:208

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

特性:
- プロセス全体で1つのインスタンス
- SentenceTransformerモデルをメモリに保持
- 初回呼び出しでモデルロード（数秒かかる）
```

## 3. 問題の分析

### 症状
既存セッション（300個のアイディア）に新しいアイディアを投稿すると、ランダムな座標に配置される。

### 原因の仮説

#### 仮説1: バックエンド再起動後のUMAPモデル喪失 ✅
```
バックエンド再起動
  ↓
_clustering_services = {} (空)
  ↓
新しいアイディア投稿
  ↓
get_clustering_service(session_id)
  ↓
session_id が辞書にない → 新規作成
  ↓
ClusteringService(umap_model=None)
  ↓
n_existing = 300 (10以上)
  ↓
CASE 3: 11個目以降の処理
  ↓
clustering_service.umap_model is None? → YES
  ↓
期待: 再クラスタリング (Line 151-173)
実際: ??? (ログが出力されていない)
```

#### 仮説2: コードが正しくロードされていない
- Line 147-148のログが表示されない
- デバッグログが一切表示されない
- → 古いコードが実行されている可能性

#### 仮説3: 別のエンドポイントが使われている
- フロントエンドが8001番ポートを指定していた（修正済み）
- 対話モードAPI（`/api/dialogue/finalize`）が使われている可能性

### デバッグ手順

1. **ログ確認**
   ```
   [IDEA-CREATE] Processing idea #301
   [IDEA-CREATE] UMAP model status: NONE or EXISTS
   [CLUSTERING-CACHE] Creating new ClusteringService...
   [CLUSTERING-CACHE] Returning cached ClusteringService...
   ```

2. **新規セッションでテスト**
   - 1個目〜9個目: ランダム座標
   - 10個目: UMAP初期化 → `[CLUSTERING] Creating new UMAP model...`
   - 11個目: UMAP使用 → `[CLUSTERING] Transforming embedding...`

3. **デバッグログ追加**
   ```python
   # Line 99の後に追加
   logger.info(f"[DEBUG] n_existing={n_existing}, umap_model={'EXISTS' if clustering_service.umap_model else 'NONE'}")
   ```

## 4. セッション作成フロー (参考)

```
POST /api/sessions
  ↓
create_session(session_data, db)
  ↓
Session作成 → データベース保存
  ↓
return session_id
```

## 5. 可視化データ取得フロー (参考)

```
GET /api/visualization/{session_id}
  ↓
get_visualization_data(session_id, db)
  ↓
├─ SELECT Idea WHERE session_id
├─ SELECT Cluster WHERE session_id
└─ return {ideas, clusters, session}
```

## 6. transform_idea() 関数について

```
backend/app/services/clustering.py:398

def transform_idea(embedding, session_id):
    service = get_clustering_service(session_id)
    return service.transform(embedding)

使用箇所:
- ❌ create_idea() では呼ばれていない
- ✅ テストコード・デバッグエンドポイントからのみ使用

create_idea() では直接:
- clustering_service.fit_transform()  (10個目)
- clustering_service.transform()      (11個目以降)
を呼んでいる
```

## まとめ

**重要な依存関係:**
1. `create_idea()` → `get_clustering_service()` → `_clustering_services` (グローバル辞書)
2. バックエンド再起動 → グローバル辞書クリア → UMAPモデル喪失
3. 11個目以降のロジック (Line 145-182) が問題の核心
4. `umap_model is None` のチェック (Line 151) が機能していない可能性

**次のアクション:**
1. バックエンドログを確認してコードが実行されているか確認
2. 新規セッションでゼロから10個投稿してテスト
3. デバッグログを追加して状態を可視化
