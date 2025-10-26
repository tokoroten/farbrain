# Debug API - クイックデモセッション作成

LLM呼び出しをスキップして、高速にテストデータを作成するためのデバッグAPIです。

## エンドポイント

### 1. クイックセッション作成 (推奨)

**最も簡単な方法**: セッションと100個のアイディアを一度に作成します。

```bash
curl -X POST http://localhost:8000/api/debug/quick-session \
  -H "Content-Type: application/json" \
  -d '{
    "title": "デモセッション - クラスタリングテスト",
    "description": "100個のアイディアでクラスタ表示をテスト",
    "idea_count": 100
  }'
```

**レスポンス例**:
```json
{
  "session_id": "abc123-...",
  "session_title": "デモセッション - クラスタリングテスト",
  "user_id": "user456-...",
  "access_url": "http://localhost:5173/session/abc123-.../join",
  "message": "Created 100 ideas",
  "created_count": 100,
  "total_ideas": 100,
  "clustered": true
}
```

### 2. 既存セッションにアイディアを一括追加

既存のセッションにアイディアを追加したい場合:

```bash
curl -X POST http://localhost:8000/api/debug/bulk-ideas \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "user_id": "your-user-id",
    "ideas": [
      "ダークモードを追加する",
      "パフォーマンスを最適化する",
      "UI/UXを改善する"
    ]
  }'
```

## 使い方

### ステップ1: クイックセッションを作成

```bash
curl -X POST http://localhost:8000/api/debug/quick-session \
  -H "Content-Type: application/json" \
  -d '{"title": "テストセッション", "idea_count": 100}'
```

### ステップ2: レスポンスから `access_url` をコピー

```json
{
  "access_url": "http://localhost:5173/session/abc123-..../join"
}
```

### ステップ3: ブラウザでURLを開く

返された `access_url` をブラウザで開くと、100個のアイディアとクラスタが表示されます。

## PowerShellでの実行例

```powershell
# クイックセッション作成
$response = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/debug/quick-session" `
  -ContentType "application/json" `
  -Body '{"title": "デモセッション", "idea_count": 100}'

Write-Host "Session created: $($response.session_id)"
Write-Host "Access URL: $($response.access_url)"

# ブラウザで開く
Start-Process $response.access_url
```

## 特徴

- ✅ **超高速**: LLM呼び出しなしで数秒で完了
- ✅ **自動クラスタリング**: 10個以上のアイディアで自動的にクラスタリング
- ✅ **埋め込み生成**: 本物の埋め込みを使用するため、クラスタリングは実際の動作と同じ
- ✅ **新規性スコア**: 正しく計算されます
- ✅ **即座にテスト可能**: セッション作成後すぐに可視化をテストできます

## 注意事項

- このAPIは**開発・デバッグ専用**です
- LLM呼び出しをスキップするため、アイディアの整形は行われません(生テキストがそのまま使用されます)
- クラスタラベルは「クラスタ 1」のようなシンプルな名前になります
- 本番環境では使用しないでください
