# Test Scripts

このディレクトリには、FarBrainの各種APIをテストするためのスクリプトが含まれています。

## スクリプト一覧

### test_openai_api.py
OpenAI APIの接続と設定をテストするスクリプト。

**使用方法:**
```bash
cd test_scripts
uv run python test_openai_api.py
```

**テスト内容:**
- API keyの読み込み
- モデル名の確認
- OpenAI APIへのリクエスト送信
- レスポンスの検証

### test_valid_models.py
様々なOpenAIモデルの有効性をテストするスクリプト。

**使用方法:**
```bash
cd test_scripts
uv run python test_valid_models.py
```

**テスト内容:**
- 複数のモデル名 (gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo)
- `max_tokens` パラメータのテスト
- `max_completion_tokens` パラメータのテスト

## トラブルシューティング

### OpenAI API 400 Error

**症状:**
```
httpx.HTTPStatusError: Client error '400 Bad Request'
```

**よくある原因:**

1. **モデル名が無効**
   - 確認: `backend/.env` の `OPENAI_MODEL` が有効なモデル名か
   - 有効なモデル: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`

2. **API keyが無効**
   - 確認: `backend/.env` の `OPENAI_API_KEY` が正しいか
   - OpenAIダッシュボードで新しいkeyを発行

3. **パラメータ名の問題**
   - 一部の新しいモデルでは `max_tokens` の代わりに `max_completion_tokens` を要求する場合がある
   - エラーメッセージで "Unsupported parameter" が表示される

### テストの実行方法

1. **環境変数の確認:**
   ```bash
   cat ../backend/.env
   ```

2. **テストスクリプトの実行:**
   ```bash
   uv run python test_openai_api.py
   ```

3. **ログの確認:**
   - Response Status が 200 であることを確認
   - エラーがある場合は Response JSON でエラー詳細を確認
