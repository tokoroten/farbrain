# FarBrain トラブルシューティングガイド

このドキュメントは、FarBrain開発中に頻繁に発生する問題とその解決方法をまとめたものです。

## 目次
1. [CORS問題](#cors問題)
2. [データベース問題](#データベース問題)
3. [ポート競合問題](#ポート競合問題)
4. [フロントエンド環境変数問題](#フロントエンド環境変数問題)
5. [開発環境のクリーンな起動方法](#開発環境のクリーンな起動方法)

---

## CORS問題

### 症状
```
Access to XMLHttpRequest at 'http://localhost:8000/api/sessions/' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### 原因
複数のバックエンドプロセスが同時に実行されており、古いプロセス（CORS設定なし）が応答している。

### 解決方法

#### 方法1: 開発環境起動スクリプトを使用（推奨）
```bash
# Windowsの場合
start-dev.bat

# または手動で全プロセスを停止
taskkill /F /IM python.exe
```

#### 方法2: 手動で古いプロセスを停止
1. 全てのPythonプロセスを停止:
```bash
taskkill /F /IM python.exe
```

2. ポートをリスンしているプロセスを確認:
```bash
netstat -ano | findstr :8000
```

3. バックエンドを再起動:
```bash
cd backend
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 予防策
- 開発開始時は必ず `start-dev.bat` を使用する
- サーバーを停止する際は、ターミナルで `Ctrl+C` を押してから閉じる
- 複数のターミナルでバックエンドを起動しない

---

## データベース問題

### 症状
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: sessions
```

### 原因
データベースファイルが存在しないか、テーブルが作成されていない。

### 解決方法

#### 方法1: バックエンドを再起動してlifespan イベントを実行
```bash
# 古いプロセスを停止
taskkill /F /IM python.exe

# バックエンドを起動（lifespanイベントでテーブルが作成される）
cd backend
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

起動ログに以下が表示されることを確認:
```
INFO:     Application startup complete.
```

その前に以下のCREATE TABLEログが表示されるはず:
```
CREATE TABLE sessions (...)
CREATE TABLE users (...)
CREATE TABLE ideas (...)
CREATE TABLE clusters (...)
```

#### 方法2: データベースを初期化
```bash
cd backend
uv run python init_db.py
```

#### 方法3: 既存のデータベースを削除して再作成
```bash
# データベースファイルを削除
rm farbrain.db

# バックエンドを起動（自動的に再作成される）
cd backend
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 予防策
- バックエンド起動時に `Application startup complete.` が表示されることを確認
- `--reload` フラグを使用している場合、コード変更時に自動リロードされるが、lifespanイベントは再実行されない場合がある
- データベースファイルを削除した場合は、バックエンドを完全に再起動する

---

## ポート競合問題

### 症状
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000):
通常、各ソケット アドレスに対してプロトコル、ネットワーク アドレス、またはポートのどれか 1 つのみを使用できます。
```

### 原因
既に別のプロセスがポート8000または5173を使用している。

### 解決方法

#### ポートを使用しているプロセスを確認
```bash
# バックエンドポート (8000) を確認
netstat -ano | findstr :8000

# フロントエンドポート (5173) を確認
netstat -ano | findstr :5173
```

#### プロセスを停止
```bash
# 全てのPythonプロセスを停止（バックエンド）
taskkill /F /IM python.exe

# 特定のPIDを停止
taskkill /F /PID <PID番号>
```

### 予防策
- 開発終了時は必ずサーバーを正しく停止する（Ctrl+C）
- `start-dev.bat` を使用して自動的に古いプロセスを停止する

---

## フロントエンド環境変数問題

### 症状
フロントエンドが誤ったポート（例: 8002）にアクセスしようとする。

### 原因
- `frontend/.env` の設定が間違っている
- Viteサーバーが環境変数の変更を検出していない

### 解決方法

#### 1. 環境変数ファイルを確認
```bash
cat frontend/.env
```

正しい設定:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

#### 2. フロントエンドを再起動
環境変数を変更した場合は、必ずViteサーバーを再起動:
```bash
# Ctrl+C でViteを停止

cd frontend
npm run dev
```

### 予防策
- `.env` ファイルを編集した後は、必ずViteサーバーを再起動
- バックエンドのポートを変更した場合は、フロントエンドの `.env` も更新

---

## 開発環境のクリーンな起動方法

### 推奨手順

#### Windows
```bash
# 1. 開発環境起動スクリプトを実行
start-dev.bat
```

このスクリプトは以下を自動実行します:
1. 全ての既存バックエンドプロセスを停止
2. バックエンドをポート8000で起動
3. フロントエンドをポート5173で起動
4. ブラウザを自動的に開く

#### 手動起動（開発中のデバッグ用）

ターミナル1（バックエンド）:
```bash
# 既存プロセスを停止
taskkill /F /IM python.exe

# バックエンド起動
cd backend
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

起動完了を確認:
```
INFO:     Application startup complete.
```

ターミナル2（フロントエンド）:
```bash
cd frontend
npm run dev
```

起動完了を確認:
```
  ➜  Local:   http://localhost:5173/
```

ブラウザで `http://localhost:5173` にアクセス。

---

## よくある問題と解決方法のチェックリスト

開発中に問題が発生したら、以下の順番で確認してください:

### ステップ1: サーバーの状態確認
```bash
# バックエンドのヘルスチェック
curl http://localhost:8000/health

# 期待される応答: {"status":"healthy"}
```

### ステップ2: ポート使用状況の確認
```bash
# バックエンドポート
netstat -ano | findstr :8000

# フロントエンドポート
netstat -ano | findstr :5173
```

### ステップ3: データベースの確認
```bash
# データベースファイルの存在確認
ls farbrain.db
```

### ステップ4: 環境変数の確認
```bash
# フロントエンド
cat frontend/.env

# バックエンド
cat backend/.env
```

### ステップ5: クリーン再起動
上記のいずれでも解決しない場合:
```bash
# 全プロセス停止
taskkill /F /IM python.exe

# データベース削除（オプション）
rm farbrain.db

# 開発環境起動
start-dev.bat
```

---

## 管理者パスワード

デフォルトの管理者パスワード: `admin123`

変更する場合は `backend/.env` を編集:
```
ADMIN_PASSWORD=your-new-password
```

---

## サポート

問題が解決しない場合は、以下の情報を含めて報告してください:

1. 症状の詳細（エラーメッセージ、スクリーンショット）
2. バックエンドのログ出力
3. ブラウザのコンソールログ
4. 実行したコマンド
5. 環境情報（OS、Pythonバージョン、Node.jsバージョン）
