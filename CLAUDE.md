## 最近の実装と改善

### LLM自動整形のスキップ機能 (2025-01-27)

**機能概要:**
- ユーザーがアイデア投稿時にLLM自動整形をスキップできるチェックボックスを追加
- チェックを外すと、入力したテキストがそのまま投稿される（LLM整形なし）

**実装箇所:**

1. **フロントエンド - IdeaInput コンポーネント** (`frontend/src/components/IdeaInput.tsx`)
   - `skipFormatting` state追加 (line 17)
   - Props interfaceに `skipFormatting?: boolean` パラメータ追加 (line 8)
   - チェックボックスUI追加 (lines 290-317) - ダイアログモードでは非表示
   - `onSubmit` に `skipFormatting` を渡す (line 147)

2. **フロントエンド - BrainstormSession** (`frontend/src/pages/BrainstormSession.tsx`)
   - `handleIdeaSubmit` に `skipFormatting?: boolean` パラメータ追加 (line 140)
   - API呼び出しに `skip_formatting` を渡す (line 148)

3. **フロントエンド - 型定義** (`frontend/src/types/api.ts`)
   - `IdeaCreateRequest` に `skip_formatting?: boolean` 追加 (line 78)
   - `IdeaVisualization` に `timestamp: string` 追加 (line 108) - Scoreboardで必要

4. **バックエンド - スキーマ** (`backend/app/schemas/idea.py`)
   - `IdeaCreate` に `skip_formatting: bool = Field(False, ...)` 追加 (lines 19-22)

5. **バックエンド - API処理** (`backend/app/api/ideas.py`)
   - `create_idea` で `skip_formatting` フラグを処理 (lines 100-108):
     ```python
     if idea_data.skip_formatting:
         formatted_text = idea_data.raw_text
     else:
         formatted_text = await llm_service.format_idea(...)
     ```

**使用方法:**
1. ブレストセッション画面でアイデア入力フォームを開く
2. 「LLM自動整形を有効にする」チェックボックスをオフにする
3. テキストを入力して投稿すると、入力したテキストがそのまま保存される

**注意点:**
- ダイアログモードでは常にLLM整形が有効（チェックボックスは非表示）
- テスト用セッション作成では自動的にLLM整形がスキップされる

---

### セッションリストの空状態UI改善 (2025-01-27)

**問題:**
- セッションが0件の場合、「セッションがありません」とだけ表示され、次のアクションが不明確
- ユーザーが何をすればよいか分からない

**解決策:**
- 「プロジェクトを作成（管理者）」ボタンを表示 (`frontend/src/pages/SessionList.tsx:174-207`)
- ボタンをクリックすると管理者ページ（`/admin`）に遷移
- より明確な次のアクションをユーザーに提示

**実装:**
```tsx
{sessions.length === 0 ? (
  <div style={{ /* ... */ }}>
    <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '1.1rem' }}>
      セッションがまだ作成されていません
    </p>
    <button onClick={() => navigate('/admin')} style={{ /* ... */ }}>
      プロジェクトを作成（管理者）
    </button>
  </div>
) : (
  // セッションリスト表示
)}
```

---

## 繰り返し発生するバグと解決方法

### LLMプロンプトバグ: format_idea() がアイデアを整形せず質問を返す

**症状:**
- `backend/app/services/llm.py` の `format_idea()` メソッドが、ユーザーのアイデアを整形せず、「もちろんです！ユーザーが入力したアイデアをお待ちしています...」のような応答を返す
- LLMがタスクを実行せず、何をすべきかを尋ねる動作になる

**根本原因:**
- プロンプト構造が不明確で、LLMがタスクの実行要求ではなく、説明要求として解釈してしまう
- インラインプロンプト方式では、ロール定義とタスクが混在し、LLMが混乱する

**解決方法:**
1. **システムプロンプト方式を使用する**
   - ロール定義（「あなたはブレインストーミングのファシリテーターです」）をシステムプロンプトとして分離
   - ユーザープロンプトには実際のタスク（整形するテキスト）のみを含める

2. **明確な原則リストを提供する**
   - システムプロンプトに箇条書きで整形原則を記載
   - 「整形後のテキストのみを出力する（説明や前置きは不要）」を明記

3. **温度パラメータの調整**
   - `temperature=0.7` で一貫性と創造性のバランスを取る

**正しい実装例:**
```python
system_prompt = """あなたはブレインストーミングセッションのファシリテーターです。
参加者の生のアイデアを、簡潔で具体的な形に整形するのがあなたの役割です。

整形の原則:
- 核心となるアイデアを明確に抽出する
- 具体的で実現可能な表現にする
- 感情的な表現を客観的に言い換える
- 1-2文で簡潔にまとめる
- 整形後のテキストのみを出力する（説明や前置きは不要）"""

prompt = f"""以下のアイデアを整形してください:

{raw_text}"""

formatted_text = await self.provider.generate(
    prompt,
    system_prompt=system_prompt,
    temperature=0.7
)
```

**検証方法:**
- `test_scripts/test_dialogue_mode.py` の `/api/dialogue/finalize` エンドポイントでテスト
- 出力に「お待ちしています」「教えてください」などのメタコメントが含まれていないことを確認

**参考:**
- backend/app/services/llm.py:210-231 (format_ideaメソッド)
- backend/app/api/dialogue.py:70-102 (finalize_ideaエンドポイント)

### クラスタ再計算でLLMラベルが生成されない問題

**症状:**
- `api.debug.forceCluster(sessionId, true)` を呼び出してもLLMによるクラスタラベルが生成されず、「クラスタ 1」「クラスタ 2」などのシンプルなラベルが返される
- データベースINSERTログに文字化け: `'�N���X�^ 2'` （これは実際には `'クラスタ 2'` の文字エンコード問題）

**調査結果:**
1. フロントエンド (`BrainstormSession.tsx:178` および `SessionList.tsx:73`) は正しく `api.debug.forceCluster(sessionId, true)` を呼び出している
2. APIクライアント (`frontend/src/lib/api.ts:122-128`) は `use_llm_labels: useLlmLabels` をリクエストボディに含めている
3. バックエンド (`backend/app/api/debug.py:395`) の Pydantic モデルは `use_llm_labels: bool = False` のデフォルト値を持つ
4. データベースログを見ると、シンプルな日本語ラベル（`クラスタ X`）が挿入されている
   - これは `if data.use_llm_labels and llm_service:` が `False` と評価されていることを意味する

**仮説:**
- リクエストボディの `use_llm_labels` フィールドがバックエンドに正しく送信されていない可能性
- FastAPIのPydanticモデルがリクエストをデシリアライズする際に問題が発生している可能性

**デバッグ追加:**
- `backend/app/api/debug.py:411` に受信したリクエストパラメータのロギングを追加
  ```python
  logger.info(f"[FORCE-CLUSTER] Received request: session_id={data.session_id}, use_llm_labels={data.use_llm_labels}")
  ```
- 次回のforce-clusterリクエストでこのログを確認し、`use_llm_labels` の実際の値を特定する必要がある

**次のステップ:**
1. ブラウザでクラスタ再計算ボタンをクリック
2. バックエンドログで `[FORCE-CLUSTER] Received request` を確認し、`use_llm_labels` の実際の値を見る
3. 値が `False` の場合、フロントエンドとバックエンド間の通信を調査
4. 値が `True` の場合、LLM初期化またはラベル生成ロジックに問題がある

**参考:**
- `backend/app/api/debug.py:391-411` (ForceClusterRequestモデルとforce_cluster エンドポイント)
- `backend/app/api/debug.py:467-494` (LLMラベル生成ロジック)
- `frontend/src/lib/api.ts:122-128` (forceCluster APIクライアント)
- `frontend/src/pages/BrainstormSession.tsx:178` (force-cluster呼び出し)
- `frontend/src/pages/SessionList.tsx:73` (force-cluster呼び出し)

---

### WebSocket接続エラー - 無限再接続ループ問題

**症状:**
- フロントエンドのコンソールに継続的に WebSocket エラーが表示される
- `WebSocket readyState: 3 (CLOSED)`
- バックエンドログに数百の WebSocket 接続開始ログが記録される

**原因:**
1. **useEffect依存関係の問題** (`frontend/src/hooks/useWebSocket.ts:110`)
   - `connect` 関数の依存配列に `onMessage`, `onOpen`, `onClose`, `onError` を含めている
   - これらのコールバックは BrainstormSession.tsx で inline で定義されているため、毎回新しい関数として扱われる
   - これにより useEffect が毎レンダリングで再実行され、WebSocket が再接続される

2. **自動再接続ロジック** (`frontend/src/hooks/useWebSocket.ts:70-74`)
   - 接続が閉じられるたびに 3秒後に再接続を試みる
   - 上記の問題と組み合わさって、無限ループが発生

**修正方法:**
- `useRef` を使用してコールバック関数の最新参照を保持し、依存配列から除外する
- これにより useEffect は sessionId が変わったときのみ再実行される

**参考:**
- `frontend/src/hooks/useWebSocket.ts:18-117` (useWebSocket フック)
- `frontend/src/pages/BrainstormSession.tsx:40-43` (useWebSocket の使用箇所)

---

## 開発プラクティス

### APIコールグラフの作成と維持

**重要性:**
- 複雑なAPIの依存関係を理解するために、コールグラフのドキュメント化が必須
- バグ調査時に関数の呼び出しフローを追跡できる
- 新機能追加時に影響範囲を把握できる

**ドキュメント:**
- `backend/API_CALL_GRAPH.md` - 主要APIのコールグラフとデータフロー
  - アイディア投稿フロー（POST /api/ideas）
  - グローバル変数とキャッシュの説明
  - ClusteringServiceのライフサイクル
  - UMAPモデルの初期化と使用タイミング

**開発時の注意:**
1. **新しいAPIエンドポイントを追加する際**
   - API_CALL_GRAPH.mdに呼び出しフローを追記する
   - 依存する関数・サービスを明記する
   - グローバル変数やキャッシュの使用があれば文書化する

2. **既存のAPIを修正する際**
   - コールグラフを確認して影響範囲を把握する
   - 修正後、コールグラフを更新する

3. **バグ調査時**
   - まずコールグラフを参照して処理フローを理解する
   - ログ出力を追加する際は、コールグラフの各ステップで状態を確認できるようにする

**例: アイディア投稿時のデバッグ**
```
問題: 同じテキストでもランダムな座標に配置される

調査手順:
1. API_CALL_GRAPH.mdでアイディア投稿フローを確認
2. CASE 3 (11個目以降) の処理を特定
3. clustering_service.umap_model の状態を確認
4. グローバル変数 _clustering_services のライフサイクルを確認
5. バックエンド再起動後の動作を理解
```

**コールグラフの書き方:**
- ASCII図で視覚的に表現
- 各ステップにファイル名と行番号を記載
- 条件分岐を明確にする
- グローバル変数の影響を明記する
- ⚠️ や ⭐ で重要なポイントを強調する

**参考:**
- `backend/API_CALL_GRAPH.md` - 完全なコールグラフドキュメント