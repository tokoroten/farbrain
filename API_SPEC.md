# FarBrain API仕様

## ベースURL

```
http://localhost:8000/api
```

## 認証

### 一般ユーザー
- ユーザーID（UUID）をlocalStorageに保存
- リクエストヘッダーまたはボディで送信

### 管理者
- `/api/admin/*` エンドポイントは管理者認証が必要
- 環境変数 `ADMIN_PASSWORD` で設定したパスワードで認証

---

## REST API

### Auth (認証)

#### ユーザー登録

```http
POST /api/auth/register
```

**Request Body:**
```json
{
  "name": "田中太郎"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "田中太郎",
  "created_at": "2025-10-25T10:00:00Z"
}
```

**説明:**
- 新規ユーザー登録時にUUIDを払い出し
- フロントエンドでlocalStorageに保存

---

#### 管理者ログイン

```http
POST /api/admin/login
```

**Request Body:**
```json
{
  "password": "admin-password"
}
```

**Response:** `200 OK`
```json
{
  "token": "jwt-token-here",
  "expires_at": "2025-10-25T22:00:00Z"
}
```

**エラー:** `401 Unauthorized`
```json
{
  "detail": "Invalid password"
}
```

---

### Sessions (セッション管理)

#### セッション作成 (管理者のみ)

```http
POST /api/admin/sessions
```

**Authorization:** `Bearer {admin_token}`

**Request Body:**
```json
{
  "title": "新規事業アイデアソン",
  "description": "2025年度の新規事業案を従来の枠にとらわれず自由に発想するブレインストーミング",
  "duration": 7200,
  "password": "session-password-optional",
  "formatting_prompt": "ユーザーの生の意見を、明確で具体的なアイディアに成形してください。\n原文: {raw_text}",
  "summarization_prompt": "以下のアイディアに共通するテーマを1-3語で要約してください。\nアイディア一覧:\n{ideas}"
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "新規事業アイデアソン",
  "description": "2025年度の新規事業案を...",
  "start_time": "2025-10-25T10:00:00Z",
  "duration": 7200,
  "status": "active",
  "has_password": true,
  "accepting_ideas": true,
  "formatting_prompt": "ユーザーの生の意見を...",
  "summarization_prompt": "以下のアイディアに...",
  "created_at": "2025-10-25T10:00:00Z"
}
```

**フィールド説明:**
- `title` (required): セッション名
- `description` (optional): セッション目的・説明
- `duration` (required): セッション時間（秒）
- `password` (optional): パスワード保護（nullableでハッシュ化して保存）
- `formatting_prompt` (optional): アイディア成形プロンプト（デフォルトあり）
- `summarization_prompt` (optional): クラスタ要約プロンプト（デフォルトあり）

---

#### セッション一覧取得

```http
GET /api/sessions
```

**Query Parameters:**
- `status` (optional): `active` | `ended`

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "新規事業アイデアソン",
      "description": "2025年度の新規事業案を...",
      "start_time": "2025-10-25T10:00:00Z",
      "duration": 7200,
      "status": "active",
      "has_password": true,
      "accepting_ideas": true,
      "participant_count": 5,
      "idea_count": 23
    }
  ]
}
```

---

#### セッション詳細取得

```http
GET /api/sessions/{session_id}
```

**Query Parameters:**
- `password` (optional): パスワード保護されている場合必須

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "新規事業アイデアソン",
  "description": "2025年度の新規事業案を...",
  "start_time": "2025-10-25T10:00:00Z",
  "duration": 7200,
  "status": "active",
  "accepting_ideas": true,
  "participant_count": 5,
  "idea_count": 23,
  "created_at": "2025-10-25T10:00:00Z"
}
```

**エラー:** `403 Forbidden` (パスワード不正)

---

#### セッション編集 (管理者のみ)

```http
PATCH /api/admin/sessions/{session_id}
```

**Authorization:** `Bearer {admin_token}`

**Request Body:**
```json
{
  "title": "新規事業アイデアソン（更新）",
  "description": "更新後の説明",
  "duration": 9000,
  "password": "new-password",
  "formatting_prompt": "更新後のプロンプト",
  "summarization_prompt": "更新後のプロンプト"
}
```

**Response:** `200 OK`

---

#### アイディア受付切り替え (管理者のみ)

```http
POST /api/admin/sessions/{session_id}/toggle-accepting
```

**Authorization:** `Bearer {admin_token}`

**Request Body:**
```json
{
  "accepting_ideas": false
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "accepting_ideas": false
}
```

**説明:**
- `accepting_ideas: true` → アイディア受付中
- `accepting_ideas: false` → アイディア受付停止（閲覧のみ）

---

#### セッション終了 (管理者のみ)

```http
POST /api/admin/sessions/{session_id}/end
```

**Authorization:** `Bearer {admin_token}`

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ended",
  "ended_at": "2025-10-25T12:00:00Z"
}
```

---

#### セッション削除 (管理者のみ)

```http
DELETE /api/admin/sessions/{session_id}
```

**Authorization:** `Bearer {admin_token}`

**Response:** `204 No Content`

---

#### セッションデータエクスポート (管理者のみ)

```http
GET /api/admin/sessions/{session_id}/export
```

**Authorization:** `Bearer {admin_token}`

**Query Parameters:**
- `format` (required): `json` | `csv`

**Response (JSON):** `200 OK`
```json
{
  "session": {
    "id": "550e8400-...",
    "title": "新規事業アイデアソン",
    "description": "2025年度の...",
    "start_time": "2025-10-25T10:00:00Z",
    "duration": 7200,
    "total_ideas": 23,
    "total_participants": 5
  },
  "users": [
    {
      "id": "660e8400-...",
      "name": "田中太郎",
      "total_score": 245.6,
      "idea_count": 12
    }
  ],
  "ideas": [
    {
      "id": "880e8400-...",
      "user_id": "660e8400-...",
      "user_name": "田中太郎",
      "raw_text": "宇宙でコーヒー栽培",
      "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
      "novelty_score": 87.5,
      "x": 12.34,
      "y": -5.67,
      "cluster_id": 2,
      "timestamp": "2025-10-25T10:15:30Z"
    }
  ],
  "clusters": [
    {
      "id": 0,
      "label": "宇宙開発・農業",
      "idea_count": 5,
      "convex_hull": [[10.0, -8.0], [15.0, -3.0], [11.0, -2.0]]
    }
  ]
}
```

**Response (CSV):** `200 OK`
```
Content-Type: text/csv
Content-Disposition: attachment; filename="新規事業アイデアソン_20251025.csv"

id,user_name,raw_text,formatted_text,novelty_score,x,y,cluster_id,cluster_label,timestamp
880e8400-...,田中太郎,宇宙でコーヒー栽培,無重力環境を活用した...,87.5,12.34,-5.67,2,宇宙開発・農業,2025-10-25T10:15:30Z
```

---

#### クラスタリング手動実行 (管理者のみ)

```http
POST /api/admin/sessions/{session_id}/recalculate
```

**Authorization:** `Bearer {admin_token}`

**Response:** `202 Accepted`
```json
{
  "message": "Clustering calculation started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**説明:**
- バックグラウンドでUMAP + k-means + 凸包 + LLM要約を実行
- 完了後、WebSocketで全参加者に配信

---

### Users (ユーザー管理)

#### セッション参加

```http
POST /api/sessions/{session_id}/join
```

**Request Body:**
```json
{
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "田中太郎",
  "password": "session-password-if-protected"
}
```

**Response:** `200 OK`
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "田中太郎",
  "total_score": 0,
  "joined_at": "2025-10-25T10:05:00Z"
}
```

**エラー:** `403 Forbidden` (パスワード不正)

---

#### セッション参加者一覧

```http
GET /api/sessions/{session_id}/users
```

**Response:** `200 OK`
```json
{
  "users": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "田中太郎",
      "total_score": 245.6,
      "idea_count": 12,
      "rank": 1
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "name": "佐藤花子",
      "total_score": 198.3,
      "idea_count": 8,
      "rank": 2
    }
  ]
}
```

---

### Ideas (アイディア管理)

#### アイディア投稿

```http
POST /api/ideas
```

**Request Body:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "raw_text": "宇宙でコーヒー栽培とかどう？"
}
```

**Response:** `201 Created`
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440000",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "raw_text": "宇宙でコーヒー栽培とかどう？",
  "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
  "embedding": [0.123, -0.456, ...],
  "x": 12.34,
  "y": -5.67,
  "cluster_id": 2,
  "novelty_score": 87.5,
  "timestamp": "2025-10-25T10:15:30Z"
}
```

**処理フロー:**
1. LLMで生の意見を成形 (OpenAI/Ollama - .env設定)
2. Sentence Transformersでベクトル化 (768次元)
3. UMAPで2次元圧縮
   - 10件未満: ランダム座標
   - 10件以上: UMAP transform適用
4. k-meansでクラスタ割り当て（最近傍法で仮割り当て）
5. 異常検知で新規性スコア算出
6. ユーザーのtotal_scoreに加算
7. WebSocketで全参加者に配信
8. 10, 20, 30...件到達時: バックグラウンドでクラスタリング全体再計算

**バリデーション:**
- `raw_text`: 1-2000文字

**エラー:** `403 Forbidden` (accepting_ideas = false の場合)

---

#### セッションのアイディア一覧

```http
GET /api/sessions/{session_id}/ideas
```

**Query Parameters:**
- `user_id` (optional): 特定ユーザーのアイディアのみ取得
- `cluster_id` (optional): 特定クラスタのアイディアのみ取得

**Response:** `200 OK`
```json
{
  "ideas": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "user_id": "660e8400-e29b-41d4-a716-446655440000",
      "user_name": "田中太郎",
      "raw_text": "宇宙でコーヒー栽培とかどう？",
      "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
      "x": 12.34,
      "y": -5.67,
      "cluster_id": 2,
      "novelty_score": 87.5,
      "timestamp": "2025-10-25T10:15:30Z"
    }
  ],
  "total": 23
}
```

---

#### アイディア削除 (管理者のみ)

```http
DELETE /api/admin/ideas/{idea_id}
```

**Authorization:** `Bearer {admin_token}`

**Response:** `204 No Content`

---

### Visualization (可視化データ)

#### セッションの可視化データ取得

```http
GET /api/sessions/{session_id}/visualization
```

**Response:** `200 OK`
```json
{
  "ideas": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "x": 12.34,
      "y": -5.67,
      "cluster_id": 2,
      "novelty_score": 87.5,
      "user_id": "660e8400-e29b-41d4-a716-446655440000",
      "user_name": "田中太郎",
      "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
      "raw_text": "宇宙でコーヒー栽培とかどう？"
    }
  ],
  "clusters": [
    {
      "id": 0,
      "label": "宇宙開発・農業",
      "convex_hull": [
        {"x": 10.0, "y": -8.0},
        {"x": 15.0, "y": -3.0},
        {"x": 11.0, "y": -2.0}
      ],
      "idea_count": 5,
      "avg_novelty_score": 72.3
    },
    {
      "id": 1,
      "label": "AI・教育",
      "convex_hull": [
        {"x": -5.0, "y": 10.0},
        {"x": -2.0, "y": 15.0},
        {"x": -8.0, "y": 12.0}
      ],
      "idea_count": 8,
      "avg_novelty_score": 65.1
    }
  ]
}
```

---

### Scoreboard (スコアボード)

#### スコアボード取得

```http
GET /api/sessions/{session_id}/scoreboard
```

**Response:** `200 OK`
```json
{
  "rankings": [
    {
      "rank": 1,
      "user_id": "660e8400-e29b-41d4-a716-446655440000",
      "user_name": "田中太郎",
      "total_score": 245.6,
      "idea_count": 12,
      "avg_novelty_score": 20.47,
      "top_idea": {
        "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
        "novelty_score": 87.5
      }
    },
    {
      "rank": 2,
      "user_id": "770e8400-e29b-41d4-a716-446655440000",
      "user_name": "佐藤花子",
      "total_score": 198.3,
      "idea_count": 8,
      "avg_novelty_score": 24.79,
      "top_idea": {
        "formatted_text": "AIが生成した夢を可視化するVRアプリ",
        "novelty_score": 92.1
      }
    }
  ]
}
```

---

## WebSocket API

### 接続

```
ws://localhost:8000/ws/{session_id}
```

**Query Parameters:**
- `user_id`: ユーザーID（UUID）
- `password` (optional): セッションパスワード（保護されている場合）

### イベント形式

すべてのメッセージはJSON形式で送受信されます。

```json
{
  "type": "event_type",
  "data": {}
}
```

---

### Client → Server イベント

#### セッション参加

```json
{
  "type": "join_session",
  "data": {
    "user_id": "660e8400-e29b-41d4-a716-446655440000",
    "user_name": "田中太郎"
  }
}
```

#### Ping (接続維持)

```json
{
  "type": "ping"
}
```

---

### Server → Client イベント

#### 接続確立

```json
{
  "type": "connected",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_count": 5
  }
}
```

#### 初期データ送信

```json
{
  "type": "initial_data",
  "data": {
    "session": {
      "id": "550e8400-...",
      "title": "新規事業アイデアソン",
      "description": "2025年度の...",
      "accepting_ideas": true
    },
    "ideas": [...],
    "clusters": [...],
    "scoreboard": {...}
  }
}
```

#### 新アイディア通知

```json
{
  "type": "new_idea",
  "data": {
    "id": "880e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440000",
    "user_name": "田中太郎",
    "raw_text": "宇宙でコーヒー栽培とかどう？",
    "formatted_text": "無重力環境を活用した宇宙空間でのコーヒー豆栽培プロジェクト",
    "x": 12.34,
    "y": -5.67,
    "cluster_id": 2,
    "novelty_score": 87.5,
    "timestamp": "2025-10-25T10:15:30Z"
  }
}
```

#### 可視化データ更新（クラスタリング再計算後）

```json
{
  "type": "visualization_update",
  "data": {
    "ideas": [...],
    "clusters": [...]
  }
}
```

#### スコアボード更新

```json
{
  "type": "scoreboard_update",
  "data": {
    "rankings": [...]
  }
}
```

#### アイディア受付状態変更

```json
{
  "type": "accepting_ideas_changed",
  "data": {
    "accepting_ideas": false,
    "message": "アイディアの受付が停止されました"
  }
}
```

#### セッション終了通知

```json
{
  "type": "session_ended",
  "data": {
    "ended_at": "2025-10-25T12:00:00Z",
    "final_rankings": [...]
  }
}
```

#### ユーザー参加/退出通知

```json
{
  "type": "user_joined",
  "data": {
    "user_id": "660e8400-e29b-41d4-a716-446655440000",
    "user_name": "田中太郎",
    "user_count": 6
  }
}
```

```json
{
  "type": "user_left",
  "data": {
    "user_id": "660e8400-e29b-41d4-a716-446655440000",
    "user_name": "田中太郎",
    "user_count": 5
  }
}
```

#### クラスタリング進行状況

```json
{
  "type": "clustering_started",
  "data": {
    "message": "クラスタリング計算を開始しました",
    "idea_count": 20
  }
}
```

```json
{
  "type": "clustering_completed",
  "data": {
    "message": "クラスタリングが完了しました",
    "cluster_count": 5
  }
}
```

#### Pong (接続維持応答)

```json
{
  "type": "pong"
}
```

---

## エラーレスポンス

すべてのエラーは以下の形式で返されます:

```json
{
  "detail": "エラーメッセージ",
  "error_code": "ERROR_CODE"
}
```

### HTTPステータスコード

- `400 Bad Request`: リクエストパラメータ不正
- `401 Unauthorized`: 管理者認証失敗
- `403 Forbidden`: パスワード不正、アイディア受付停止中
- `404 Not Found`: リソースが存在しない
- `422 Unprocessable Entity`: バリデーションエラー
- `429 Too Many Requests`: レート制限超過
- `500 Internal Server Error`: サーバーエラー
- `503 Service Unavailable`: 外部API (LLM) エラー

### エラーコード例

- `SESSION_NOT_FOUND`: セッションが存在しない
- `SESSION_ENDED`: セッションが既に終了している
- `SESSION_PASSWORD_REQUIRED`: パスワードが必要
- `INVALID_PASSWORD`: パスワードが不正
- `IDEAS_NOT_ACCEPTING`: アイディア受付停止中
- `USER_NOT_FOUND`: ユーザーが存在しない
- `INVALID_INPUT`: 入力値が不正
- `TEXT_TOO_LONG`: テキストが長すぎる（2000文字超過）
- `LLM_SERVICE_ERROR`: LLMサービスエラー
- `EMBEDDING_ERROR`: ベクトル化エラー
- `CLUSTERING_ERROR`: クラスタリングエラー
- `UNAUTHORIZED`: 管理者認証が必要

---

## クラスタリング仕様

### 実行タイミング
- **10件ごと**: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110...
- **手動実行**: 管理者が任意のタイミングで実行可能

### クラスタ数の決定
```python
import math
n_clusters = max(5, math.ceil(len(ideas) ** (1/3)))
```

**例:**
- 10件: 5クラスタ
- 27件: 5クラスタ
- 125件: 5クラスタ
- 216件: 6クラスタ
- 1000件: 10クラスタ

### クラスタ要約サンプリング
- 各クラスタから**10件**ランダムサンプリング
- 10件未満のクラスタ: 全件サンプリング

### UMAP適用
- **1-9件**: ランダム座標 `(-10, 10)` の範囲
- **10件到達**: 初回 `fit_transform`
- **11件以降**: `transform` で追加
- **10件ごと**: 全体を `fit_transform` で再計算

---

## レート制限

現在のMVP版では実装なし。将来的に以下を検討:

- `/api/ideas`: 1ユーザーあたり 10リクエスト/分
- その他のエンドポイント: 100リクエスト/分

---

## バージョニング

現在: `v1` (URLパスに含めず、`/api/`直下)

将来的にAPIバージョンが変更される場合は `/api/v2/` のように明示する。
