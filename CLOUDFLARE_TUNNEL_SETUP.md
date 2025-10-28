# Cloudflare Tunnelでの公開手順

このガイドでは、Cloudflare Tunnelを使ってローカル環境のFarBrainをインターネットに公開する方法を説明します。

## 前提条件

- Cloudflareアカウント（無料でOK）
- ドメイン（Cloudflareに登録済み）
- バックエンドとフロントエンドがローカルで起動している

## ステップ 1: cloudflaredのインストール

### Windowsの場合

PowerShellで実行：

```powershell
winget install --id Cloudflare.cloudflared
```

または、[公式サイト](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)からインストーラーをダウンロード。

インストール確認：

```bash
cloudflared --version
```

## ステップ 2: Cloudflareにログイン

```bash
cloudflared tunnel login
```

ブラウザが開くので、Cloudflareアカウントでログインし、トンネルを作成するドメインを選択します。

## ステップ 3: トンネルを作成

```bash
cloudflared tunnel create farbrain
```

出力例：
```
Tunnel credentials written to C:\Users\shinta\.cloudflared\xxxxx-xxxx-xxxx-xxxx-xxxxx.json
Tunnel ID: xxxxx-xxxx-xxxx-xxxx-xxxxx
```

**重要**: トンネルIDをメモしておいてください。

## ステップ 4: 設定ファイルを編集

プロジェクトルートの `cloudflare-tunnel-config.yml` を編集：

```yaml
tunnel: YOUR_TUNNEL_ID_HERE  # ←ここにトンネルIDを入力
credentials-file: C:\Users\shinta\.cloudflared\YOUR_TUNNEL_ID_HERE.json  # ←ここも

ingress:
  # Frontend (Vite dev server)
  - hostname: farbrain.yourdomain.com  # ←あなたのドメインに変更
    service: http://localhost:5173
    originRequest:
      noTLSVerify: true

  # Backend API
  - hostname: api-farbrain.yourdomain.com  # ←あなたのドメインに変更
    service: http://localhost:8000
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      noHappyEyeballs: true

  - service: http_status:404
```

## ステップ 5: DNSレコードを作成

各ホスト名に対してCNAMEレコードを作成：

```bash
cloudflared tunnel route dns farbrain farbrain.yourdomain.com
cloudflared tunnel route dns farbrain api-farbrain.yourdomain.com
```

## ステップ 6: フロントエンドの環境変数を設定

`frontend/.env` ファイルを作成（または編集）：

```env
VITE_API_URL=https://api-farbrain.yourdomain.com
VITE_WS_URL=wss://api-farbrain.yourdomain.com
```

**注意**: `https` と `wss` を使用してください（Cloudflare Tunnelは自動的にTLS化されます）。

## ステップ 7: サービスを起動

### 1. バックエンドを起動（別ターミナル）

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. フロントエンドを起動（別ターミナル）

```bash
cd frontend
npm run dev
```

### 3. Cloudflare Tunnelを起動（別ターミナル）

プロジェクトルートで：

```bash
cloudflared tunnel --config cloudflare-tunnel-config.yml run farbrain
```

## ステップ 8: アクセス確認

ブラウザで以下にアクセス：

- **フロントエンド**: `https://farbrain.yourdomain.com`
- **バックエンドAPI**: `https://api-farbrain.yourdomain.com/docs` (Swagger UI)

## トラブルシューティング

### WebSocketが接続できない

- `cloudflare-tunnel-config.yml` の `connectTimeout` を増やす
- バックエンドのCORS設定を確認（`app/core/config.py`）

### フロントエンドからAPIに接続できない

- `frontend/.env` の `VITE_API_URL` を確認
- ブラウザのDevToolsでネットワークタブを確認
- バックエンドのログを確認

### トンネルが起動しない

```bash
# トンネル状態を確認
cloudflared tunnel info farbrain

# トンネルを削除して作り直し
cloudflared tunnel delete farbrain
cloudflared tunnel create farbrain
```

## 本番環境での運用（推奨）

ローカル開発ではなく本番運用する場合：

### 1. フロントエンドをビルド

```bash
cd frontend
npm run build
```

### 2. 静的ファイルを配信

Nginxやcaddy、または `python -m http.server` で `frontend/dist` を配信。

### 3. トンネルを自動起動（サービス化）

```bash
cloudflared service install
```

## セキュリティ注意事項

- **環境変数**: `.env` ファイルは `.gitignore` に追加済み
- **管理者パスワード**: `backend/app/core/config.py` の `ADMIN_PASSWORD` を変更
- **OpenAI API Key**: 本番環境では環境変数で設定

## コスト

Cloudflare Tunnelは無料で使用できます。帯域幅制限もありません。

## 参考リンク

- [Cloudflare Tunnel公式ドキュメント](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
