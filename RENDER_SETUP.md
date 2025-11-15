# Render デプロイメント - 環境変数セットアップ

## 問題

バックエンドは起動していますが、CORSエラーが発生しています：
```
Access to XMLHttpRequest at 'https://farbrain-api.onrender.com/health' from origin 'https://farbrain.onrender.com' has been blocked by CORS policy
```

これは環境変数がRenderダッシュボードに設定されていないことが原因です。

## 解決方法

### Option 1: Render ダッシュボードから設定（推奨）

1. **Render ダッシュボードにアクセス**
   - https://dashboard.render.com/
   - `farbrain-api` サービスを選択

2. **Environment タブを開く**

3. **以下の環境変数を追加/確認：**

   ```
   OPENAI_API_KEY = sk-... (あなたのOpenAI APIキー)
   ADMIN_PASSWORD = (管理者用パスワード)
   CORS_ORIGINS = https://farbrain.onrender.com,http://localhost:5173
   DATABASE_URL = (自動設定済み - 確認のみ)
   SECRET_KEY = (自動生成済み - 確認のみ)
   OPENAI_MODEL = gpt-4o-mini
   DEBUG = false
   LOG_LEVEL = INFO
   ```

4. **Save Changes をクリック**
   - サービスが自動的に再デプロイされます（約1-2分）

5. **デプロイ完了を待つ**
   - Logs タブで起動ログを確認
   - `Application startup complete` が表示されればOK

### Option 2: Render CLI から設定

```bash
# Render CLI をインストール（未インストールの場合）
npm install -g render-cli

# ログイン
render login

# 環境変数を設定
render env set OPENAI_API_KEY="sk-..." --service farbrain-api
render env set ADMIN_PASSWORD="your-password" --service farbrain-api
render env set CORS_ORIGINS="https://farbrain.onrender.com,http://localhost:5173" --service farbrain-api
```

## 確認方法

### 1. バックエンドの health check

ブラウザで以下にアクセス：
```
https://farbrain-api.onrender.com/health
```

以下のレスポンスが返ればOK：
```json
{"status": "healthy"}
```

### 2. フロントエンドからの接続確認

https://farbrain.onrender.com にアクセスして：
- セッション一覧が表示される
- コンソールにCORSエラーが出ない

## トラブルシューティング

### バックエンドが起動しない場合

1. **Render ダッシュボード → farbrain-api → Logs** を確認

2. **よくあるエラー：**

   **エラー:** `OPENAI_API_KEY not set`
   **解決:** OpenAI APIキーを環境変数に設定

   **エラー:** `Database connection failed`
   **解決:** DATABASE_URL が正しく設定されているか確認

   **エラー:** `ModuleNotFoundError`
   **解決:** requirements.txt にモジュールが含まれているか確認

3. **ログの見方：**
   ```
   [INFO] Application startup complete  ← 起動成功
   [ERROR] ...                           ← エラー発生
   ```

### フロントエンドからアクセスできない場合

1. **CORS_ORIGINS を確認**
   - `https://farbrain.onrender.com` が含まれているか
   - カンマ区切りになっているか（スペースなし）

2. **ブラウザのコンソールを確認**
   - CORS エラー → CORS_ORIGINS を修正
   - 404 エラー → バックエンドが起動していない
   - Network Error → バックエンドがスリープ中（15分アクセスがないとスリープ）

3. **バックエンドをウェイクアップ**
   - https://farbrain-api.onrender.com/health に直接アクセス
   - 初回は30秒ほどかかる場合があります（Free tier のため）

## 次のステップ

環境変数を設定したら：
1. Render ダッシュボードで再デプロイを待つ
2. https://farbrain-api.onrender.com/health にアクセスして確認
3. https://farbrain.onrender.com でアプリケーションをテスト
