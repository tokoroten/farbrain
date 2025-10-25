# FarBrain セットアップガイド

## 前提条件

### 必須環境
- **Node.js**: v18.0.0 以上
- **Python**: 3.10 以上
- **npm** または **yarn**
- **pip**: 最新版推奨
- **Git**

### 必要なアカウント
- **OpenAI API**: GPT-4 および Embeddings API へのアクセス
  - https://platform.openai.com/signup

---

## プロジェクトのクローン

```bash
git clone https://github.com/yourusername/farbrain.git
cd farbrain
```

---

## バックエンドセットアップ

### 1. ディレクトリ構造作成

```bash
mkdir -p backend/app/{routers,services,schemas}
cd backend
```

### 2. Python仮想環境の作成

#### Windows (Git Bash / PowerShell)
```bash
python -m venv venv
source venv/Scripts/activate  # Git Bash
# または
.\venv\Scripts\Activate.ps1   # PowerShell
```

#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージのインストール

`requirements.txt` を作成:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
sqlalchemy==2.0.23
sentence-transformers==2.2.2
torch==2.1.0
numpy==1.26.2
scikit-learn==1.3.2
umap-learn==0.5.5
scipy==1.11.4
websockets==12.0
python-multipart==0.0.6

# Optional: OpenAI for LLM-based idea formatting
openai==1.3.5
```

インストール:

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env` ファイルを作成:

```bash
# backend/.env

# LLM Provider (openai or ollama)
LLM_PROVIDER=openai
# LLM_PROVIDER=ollama

# OpenAI Settings (if LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# Ollama Settings (if LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Embedding Model (Sentence Transformers)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
# EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Database
DATABASE_URL=sqlite:///./farbrain.db

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Security
SECRET_KEY=your-secret-key-here-change-in-production
```

**重要**: `.env` ファイルは `.gitignore` に追加してコミットしないこと

### 5. データベース初期化

```bash
# backend ディレクトリで実行
python -m app.database
```

---

## フロントエンドセットアップ

### 1. プロジェクト作成

```bash
cd ../  # プロジェクトルートに戻る
npm create vite@latest frontend -- --template react-ts
cd frontend
```

### 2. 依存パッケージのインストール

```bash
npm install
```

追加パッケージのインストール:

```bash
npm install d3 @types/d3
npm install axios
npm install recharts
npm install zustand  # 状態管理
```

### 3. 環境変数の設定

`.env` ファイルを作成:

```bash
# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

---

## 開発サーバーの起動

### ターミナル1: バックエンド起動

```bash
cd backend
source venv/Scripts/activate  # 仮想環境がアクティブでない場合

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

起動確認: http://localhost:8000/docs (FastAPI自動生成ドキュメント)

### ターミナル2: フロントエンド起動

```bash
cd frontend
npm run dev
```

起動確認: http://localhost:5173

---

## データベースについて

### SQLite (デフォルト、開発用)

- ファイル: `backend/farbrain.db`
- 設定不要、自動作成
- 単一ファイルで管理が簡単

### PostgreSQL (本番推奨)

#### インストール

**Windows:**
https://www.postgresql.org/download/windows/

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### データベース作成

```bash
psql -U postgres
CREATE DATABASE farbrain;
CREATE USER farbrain_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE farbrain TO farbrain_user;
\q
```

#### 環境変数更新

```bash
# backend/.env
DATABASE_URL=postgresql://farbrain_user:your_password@localhost/farbrain
```

#### 追加パッケージ

```bash
pip install psycopg2-binary
```

---

## LLM設定

### オプション1: OpenAI (クラウド、有料)

#### 1. APIキーの取得

1. https://platform.openai.com/ にログイン
2. 左メニュー「API Keys」をクリック
3. 「Create new secret key」でキー生成
4. キーをコピー (一度しか表示されない)

#### 2. 環境変数に設定

```bash
# backend/.env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4
```

#### 3. コスト見積もり (2025年10月時点)

**GPT-4 (意見成形・クラスタ要約):**
- Input: $0.03 / 1K tokens
- Output: $0.06 / 1K tokens

**目安:**
- 1セッション (2時間、5人、100アイディア想定)
- 意見成形: 約 $0.50
- クラスタ要約: 約 $0.10
- **合計: 約 $0.60 / セッション**

使用量確認: https://platform.openai.com/usage

### オプション2: Ollama (ローカル、無料)

#### 1. Ollamaのインストール

**Windows/macOS/Linux:**
https://ollama.ai/download

#### 2. モデルのダウンロード

```bash
ollama pull llama2
# または他のモデル
ollama pull mistral
ollama pull codellama
```

#### 3. Ollama起動

```bash
ollama serve
```

デフォルトで http://localhost:11434 で起動

#### 4. 環境変数に設定

```bash
# backend/.env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

**メリット:**
- 完全無料
- プライバシー保護 (データが外部に送信されない)
- オフライン動作可能

**デメリット:**
- GPUが推奨 (CPUでも動作するが遅い)
- モデルサイズが大きい (数GB)

---

## Sentence Transformers (Embedding)

Sentence Transformersは**ローカルで動作**し、外部APIは不要です。

### 初回起動時の挙動

初回起動時、指定したモデルが自動的にダウンロードされます:

```bash
# .envで指定したモデル (例: all-MiniLM-L6-v2) が
# ~/.cache/torch/sentence_transformers/ にダウンロードされる
```

### 推奨モデル

**all-MiniLM-L6-v2** (デフォルト):
- サイズ: 約 90MB
- 次元: 384
- 速度: 非常に高速
- 言語: 英語メイン

**paraphrase-multilingual-MiniLM-L12-v2**:
- サイズ: 約 470MB
- 次元: 384
- 速度: 高速
- 言語: 多言語対応 (日本語含む)

**all-mpnet-base-v2**:
- サイズ: 約 420MB
- 次元: 768
- 速度: 中速
- 言語: 英語、高精度

### GPU加速 (オプション)

PyTorch with CUDA をインストールすることでGPU加速が可能:

```bash
# CUDA 11.8の場合
pip install torch==2.1.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
```

GPUがない場合でもCPUで十分高速に動作します。

---

## トラブルシューティング

### バックエンドが起動しない

#### エラー: `ModuleNotFoundError: No module named 'app'`

**解決策:**
```bash
# backend ディレクトリから実行していることを確認
cd backend
python -c "import sys; print(sys.path)"

# PYTHONPATH を設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn app.main:app --reload
```

#### エラー: `ImportError: cannot import name 'create_engine'`

**解決策:**
```bash
pip install --upgrade sqlalchemy
```

### フロントエンドが起動しない

#### エラー: `Cannot find module 'd3'`

**解決策:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### OpenAI APIエラー

#### エラー: `AuthenticationError: Incorrect API key`

**解決策:**
1. `.env` ファイルのAPIキーを確認
2. 先頭に `sk-` があることを確認
3. キーにスペースが含まれていないか確認

#### エラー: `RateLimitError`

**解決策:**
1. https://platform.openai.com/account/limits で上限を確認
2. リクエストレートを下げる (バックエンドでリトライロジック実装)
3. 有料プランへのアップグレード検討

### CORS エラー

#### エラー: `Access to fetch at ... from origin ... has been blocked by CORS policy`

**解決策:**
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### WebSocket 接続エラー

#### エラー: `WebSocket connection failed`

**解決策:**
1. バックエンドが起動しているか確認
2. ブラウザコンソールでエラー詳細を確認
3. ファイアウォール設定を確認

---

## 本番環境デプロイ (参考)

### バックエンド (例: Railway, Render, Fly.io)

1. PostgreSQLデータベースをプロビジョニング
2. 環境変数を設定
3. `Procfile` または `fly.toml` 作成
4. デプロイコマンド実行

### フロントエンド (例: Vercel, Netlify)

1. リポジトリを連携
2. ビルド設定: `npm run build`
3. 出力ディレクトリ: `dist`
4. 環境変数 (APIエンドポイント) を設定

---

## 開発のヒント

### ホットリロード

- **バックエンド**: `--reload` フラグで自動リロード
- **フロントエンド**: Viteが自動的にホットリロード

### デバッグ

**バックエンド:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**フロントエンド:**
```typescript
console.log('Debug info:', data)
```

### API テスト

- **Swagger UI**: http://localhost:8000/docs
- **cURL**:
```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session", "duration": 7200}'
```

### データベースリセット

```bash
# SQLiteの場合
rm backend/farbrain.db
python -m app.database

# PostgreSQLの場合
psql -U farbrain_user -d farbrain -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python -m app.database
```

---

## 次のステップ

セットアップが完了したら:

1. [ARCHITECTURE.md](ARCHITECTURE.md) でシステム構成を理解
2. [API_SPEC.md](API_SPEC.md) でAPI仕様を確認
3. `backend/app/main.py` と `frontend/src/App.tsx` からコードを読み始める

Happy Coding!
