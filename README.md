# FarBrain - LLMゲーミフィケーションブレストツール

## 概要

FarBrainは、AIを活用した革新的なブレインストーミングツールです。参加者が「常識から遠い」新規性の高いアイディアを出すことを競い合い、創造的思考を促進します。

## 特徴

### コアコンセプト
- **生の意見 → AI整形**: 参加者の自由な発想をLLMが適切なアイディアに整形
- **ベクトル化 & 新規性スコアリング**: Sentence Transformersで意見をベクトル化し、既存アイディアとの距離で新規性を評価
- **ゲーミフィケーション**: 新規性が高いほど高得点。リアルタイムスコアボードで競争

### ビジュアライゼーション
- **UMAP次元圧縮**: 768次元ベクトルを2次元に圧縮して可視化
- **k-meansクラスタリング**: 類似アイディアを自動グループ化（件数の立方根個のクラスタ）
- **凸包表示**: クラスタの範囲を視覚的に表現
- **AIラベル生成**: 各クラスタの内容をLLMが自動要約（10件サンプリング）

### マルチプレイヤーセッション
- **柔軟なセッション時間**: デフォルト2時間、最大24時間まで設定可能
- **リアルタイム同期**: WebSocketによる即座の更新
- **ユーザー別トラッキング**: 個人の貢献度を可視化
- **スコアボード**: 参加者のランキングをリアルタイム表示

## 技術スタック

### フロントエンド
- **React + TypeScript**: 型安全なUI実装
- **Vite**: 高速ビルドツール
- **Canvas API**: インタラクティブな可視化
- **WebSocket**: リアルタイム通信
- **Zustand**: 状態管理（localStorage永続化）
- **React Router**: ルーティング
- **Axios**: HTTP クライアント

### バックエンド
- **FastAPI**: 高速なPython Webフレームワーク
- **SQLAlchemy**: 非同期ORM
- **SQLite**: 開発用データベース（PostgreSQL対応可能）
- **OpenAI API**: アイディア整形とクラスタラベル生成
- **uv**: Python環境管理

### 機械学習
- **Sentence Transformers**: 多言語埋め込み（paraphrase-multilingual-mpnet-base-v2, 768次元）
- **UMAP**: 次元圧縮（768→2次元）
- **scikit-learn**: k-meansクラスタリング
- **SciPy**: 凸包計算

### 新規性スコアリング
5つの変換関数から選択可能：
- **Linear Distance**: 平均コサイン距離ベース
- **Min Distance**: 最小距離ベース
- **Exponential Distance**: 指数変換
- **Percentile Distance**: パーセンタイル変換
- **Top-K Distance**: 上位K件の平均距離

## プロジェクト構成

```
farbrain/
├── frontend/                    # Reactフロントエンド
│   ├── src/
│   │   ├── components/          # 再利用可能なコンポーネント
│   │   ├── pages/               # ページコンポーネント
│   │   ├── hooks/               # カスタムフック
│   │   ├── store/               # Zustand状態管理
│   │   ├── lib/                 # APIクライアント
│   │   └── types/               # TypeScript型定義
│   └── package.json
├── backend/                     # FastAPIバックエンド
│   ├── app/
│   │   ├── api/                 # APIルーター
│   │   ├── core/                # 設定・ユーティリティ
│   │   ├── db/                  # データベース設定
│   │   ├── models/              # SQLAlchemyモデル
│   │   ├── schemas/             # Pydanticスキーマ
│   │   ├── services/            # ビジネスロジック
│   │   └── websocket/           # WebSocket管理
│   ├── tests/                   # ユニットテスト
│   └── pyproject.toml           # uv設定
├── start_backend.sh/bat         # バックエンド起動スクリプト
├── start_frontend.sh/bat        # フロントエンド起動スクリプト
├── README.md                    # このファイル
├── ARCHITECTURE.md              # アーキテクチャ詳細
├── API_SPEC.md                  # API仕様
└── SETUP.md                     # セットアップ手順
```

## クイックスタート

### 必要な環境
- **Node.js** 18+ (フロントエンド)
- **Python** 3.11+ (バックエンド)
- **uv** ([インストール手順](https://github.com/astral-sh/uv))
- **OpenAI APIキー**

### 1. リポジトリをクローン
```bash
git clone <repository-url>
cd farbrain
```

### 2. バックエンド設定

```bash
# .envファイルを作成
cp backend/.env.example backend/.env

# .envを編集してOpenAI APIキーを設定
# OPENAI_API_KEY=sk-your-key-here
```

### 3. フロントエンド設定

```bash
# .envファイルを作成（デフォルト値でOK）
cp frontend/.env.example frontend/.env
```

### 4. 起動

**Linux/Mac:**
```bash
# ターミナル1: バックエンド起動
./start_backend.sh

# ターミナル2: フロントエンド起動
./start_frontend.sh
```

**Windows:**
```cmd
# コマンドプロンプト1: バックエンド起動
start_backend.bat

# コマンドプロンプト2: フロントエンド起動
start_frontend.bat
```

### 5. アクセス

- フロントエンド: http://localhost:5173
- バックエンドAPI: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

## 使い方

### 1. 名前を登録
初回アクセス時に名前を入力（localStorageに永続化）

### 2. セッションを作成（管理者）
- 「管理者ページ」からセッションを作成
- タイトル、説明、時間、パスワードを設定
- カスタムプロンプトも設定可能（オプション）

### 3. セッションに参加
- セッション一覧から参加したいセッションを選択
- パスワード保護されている場合は入力

### 4. アイディアを投稿
- テキストエリアにアイディアを入力（最大2000文字）
- LLMが自動整形し、新規性スコアを計算
- リアルタイムで可視化に反映

### 5. 可視化を楽しむ
- ドラッグでパン、ホイールでズーム
- アイディアをクリックして詳細表示
- 10件ごとにクラスタリング＆ラベル生成

### 6. スコアボードで競う
- リアルタイムランキング
- 自分の順位と最高スコアアイディアを確認

## API エンドポイント

### セッション管理
- `POST /api/sessions/` - セッション作成
- `GET /api/sessions/` - セッション一覧
- `GET /api/sessions/{id}` - セッション詳細
- `POST /api/sessions/{id}/end` - セッション終了
- `POST /api/sessions/{id}/toggle-accepting` - アイディア受付切り替え

### ユーザー管理
- `POST /api/users/register` - ユーザー登録
- `POST /api/users/{session_id}/join` - セッション参加

### アイディア
- `POST /api/ideas/` - アイディア投稿
- `GET /api/ideas/{session_id}` - セッション内のアイディア一覧

### 可視化
- `GET /api/visualization/{session_id}` - 可視化データ取得
- `GET /api/visualization/{session_id}/scoreboard` - スコアボード取得

### WebSocket
- `WS /ws/{session_id}` - リアルタイム更新

## WebSocketイベント

### サーバー→クライアント
- `idea_created` - 新規アイディア投稿
- `coordinates_updated` - UMAP座標更新
- `clusters_updated` - クラスタ情報更新
- `user_joined` - ユーザー参加
- `scoreboard_updated` - スコアボード更新
- `session_status_changed` - セッション状態変更

## 開発

### テスト実行
```bash
cd backend
uv run pytest
```

### コード整形
```bash
cd backend
uv run black .
uv run isort .
```

### 型チェック
```bash
cd backend
uv run mypy .
```

## トラブルシューティング

### ポート競合
デフォルトでバックエンドは8000番、フロントエンドは5173番を使用します。
変更する場合は各起動スクリプトとフロントエンドの`.env`を編集してください。

### OpenAI API エラー
- APIキーが正しく設定されているか確認
- APIの使用制限に達していないか確認
- ネットワーク接続を確認

### データベースエラー
初回起動時にテーブルが自動作成されます。問題がある場合は`backend/farbrain.db`を削除して再起動してください。

## ライセンス

MIT License

## 貢献

Issue、Pull Requestを歓迎します。

## 参考ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) - システムアーキテクチャ詳細
- [API_SPEC.md](API_SPEC.md) - API仕様書
- [SETUP.md](SETUP.md) - 詳細セットアップ手順

## 作者

FarBrain Development Team
