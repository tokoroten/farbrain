# Render.com へのデプロイ手順

FarBrainをRender.comの無料枠にデプロイする手順です。

## 前提条件

- GitHubアカウント
- Render.comアカウント（GitHubでログイン可能）
- GitHub CLI (`gh`) がインストール済み
- OpenAI APIキー

## デプロイ構成

Renderの無料枠で以下をデプロイします：

1. **PostgreSQL Database** (1GB無料)
2. **FastAPI Backend** (Web Service, 750時間/月無料)
3. **React Frontend** (Static Site, 無料)

## ステップ1: GitHub Secretsの設定

まず、機密情報をGitHub Secretsに設定します：

```bash
# OpenAI APIキーを設定
gh secret set OPENAI_API_KEY

# プロンプトが表示されたら、APIキーを入力してEnter

# 管理者パスワードを設定
gh secret set ADMIN_PASSWORD

# プロンプトが表示されたら、パスワードを入力してEnter
```

確認：
```bash
gh secret list
```

## ステップ2: Render.comでリポジトリを連携

1. [Render Dashboard](https://dashboard.render.com/) にアクセス
2. 「New」→「Blueprint」を選択
3. GitHubリポジトリ `tokoroten/farbrain` を選択
4. `render.yaml` が自動検出されます
5. 「Apply」をクリック

Renderが自動的に以下を作成します：
- PostgreSQLデータベース (`farbrain-db`)
- バックエンドサービス (`farbrain-api`)
- フロントエンドサイト (`farbrain-frontend`)

## ステップ3: 環境変数の設定

Renderダッシュボードで、バックエンドサービス (`farbrain-api`) の環境変数を追加設定します：

### 必須設定

1. **OPENAI_API_KEY**
   - Render Dashboard → `farbrain-api` → Environment
   - 「Add Environment Variable」をクリック
   - Key: `OPENAI_API_KEY`
   - Value: あなたのOpenAI APIキー
   - 「Save Changes」

2. **ADMIN_PASSWORD**
   - Key: `ADMIN_PASSWORD`
   - Value: 管理者パスワード（セッション作成用）
   - 「Save Changes」

### 自動設定される環境変数

以下は `render.yaml` で自動設定されます：

- `DATABASE_URL` - PostgreSQLの接続文字列（自動）
- `SECRET_KEY` - ランダム生成（自動）
- `CORS_ORIGINS` - フロントエンドURL
- `OPENAI_MODEL` - `gpt-4o-mini`（コスト削減版）

## ステップ4: デプロイ確認

1. Renderが自動的にビルドとデプロイを開始します
2. デプロイ完了まで5-10分程度かかります

### アクセスURL

デプロイが完了すると、以下のURLでアクセスできます：

- **フロントエンド**: `https://farbrain-frontend.onrender.com`
- **バックエンドAPI**: `https://farbrain-api.onrender.com`
- **API Docs**: `https://farbrain-api.onrender.com/docs`

## ステップ5: 動作確認

1. フロントエンドURL にアクセス
2. 管理者ページ (`/admin`) でセッションを作成
3. セッションに参加してアイデアを投稿

## トラブルシューティング

### ビルドエラー

**症状**: バックエンドのビルドが失敗する

**解決策**:
- Render Dashboard → `farbrain-api` → Logs でエラーを確認
- `requirements.txt` が正しく生成されているか確認
- Python バージョンを確認（Python 3.11+が必要）

### データベース接続エラー

**症状**: `could not connect to server`

**解決策**:
- `DATABASE_URL` 環境変数が正しく設定されているか確認
- Render Dashboard → `farbrain-db` → Status が "Available" か確認

### 無料プランの制限

**スリープ**: 15分間アクセスがないとサービスがスリープします
- 再アクセス時に起動まで30秒〜1分かかります
- 有料プラン（$7/月）で常時起動可能

**データベース容量**: 1GB制限
- 定期的に古いセッションを削除することを推奨

## 自動デプロイ

`main` ブランチに push すると、自動的に再デプロイされます：

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Renderが自動的に：
1. 新しいコードを pull
2. ビルド
3. デプロイ

## カスタムドメイン設定（オプション）

Renderの無料プランでもカスタムドメインを設定できます：

1. Render Dashboard → `farbrain-frontend` → Settings → Custom Domains
2. 「Add Custom Domain」
3. ドメインのDNSレコードを設定（指示に従う）

## コスト最適化

無料枠を最大限活用するためのヒント：

1. **OpenAI API**:
   - `gpt-4o-mini` を使用（`render.yaml`でデフォルト設定済み）
   - 本番環境では `gpt-4` より90%安い

2. **Render**:
   - 無料枠: 750時間/月（約1ヶ月稼働）
   - スリープを許容すれば完全無料

3. **データベース**:
   - 1GB制限内に収める
   - 定期的にクリーンアップ

## 参考リンク

- [Render Blueprints](https://render.com/docs/blueprint-spec)
- [Render Free Tier](https://render.com/docs/free)
- [PostgreSQL on Render](https://render.com/docs/databases)
