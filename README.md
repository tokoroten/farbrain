# FarBrain - LLMゲーミフィケーションブレストツール

## 概要

FarBrainは、AIを活用した革新的なブレインストーミングツールです。参加者が「常識から遠い」新規性の高いアイディアを出すことを競い合い、創造的思考を促進します。

## 特徴

### コアコンセプト
- **生の意見 → AI成形**: 参加者の自由な発想をLLMが適切なアイディアに整形
- **ベクトル化 & 新規性スコアリング**: OpenAI Embeddingsで意見をベクトル化し、既存アイディアとの距離で新規性を評価
- **ゲーミフィケーション**: 新規性が高いほど高得点。リアルタイムスコアボードで競争

### ビジュアライゼーション
- **UMAP次元圧縮**: 高次元ベクトルを2次元に圧縮して可視化
- **k-meansクラスタリング**: 類似アイディアを自動グループ化
- **凸包表示**: クラスタの範囲を視覚的に表現
- **AIラベル生成**: 各クラスタの内容をLLMが自動要約

### マルチプレイヤーセッション
- **2時間の集中セッション**: タイマー付きブレスト環境
- **リアルタイム同期**: WebSocketによる即座の更新
- **ユーザー別トラッキング**: 個人の貢献度を可視化
- **スコアボード**: 参加者のランキングをリアルタイム表示

## 技術スタック

### フロントエンド
- React + TypeScript
- Vite (ビルドツール)
- D3.js (データ可視化)
- WebSocket (リアルタイム通信)

### バックエンド
- FastAPI (Python)
- SQLAlchemy (ORM)
- SQLite/PostgreSQL (データベース)
- OpenAI API (LLM & Embeddings)

### 機械学習
- UMAP (次元圧縮)
- scikit-learn (k-means, 異常検知)
- NumPy, SciPy (数値計算、凸包)

## ユースケース

### 企業のアイデアソン
新規事業開発、製品企画のブレインストーミングセッション

### 教育現場
創造的思考を促すワークショップ、デザイン思考の実践

### 研究・開発
既存の枠を超えたアイディア探索、イノベーション促進

## プロジェクト構成

```
farbrain/
├── frontend/           # Reactフロントエンド
├── backend/            # FastAPIバックエンド
├── docs/               # ドキュメント
├── README.md           # このファイル
├── ARCHITECTURE.md     # アーキテクチャ詳細
├── API_SPEC.md         # API仕様
└── SETUP.md            # セットアップ手順
```

## クイックスタート

詳細なセットアップ手順は [SETUP.md](SETUP.md) を参照してください。

### 必要な環境
- Node.js 18+
- Python 3.10+
- OpenAI APIキー

### 基本的な起動手順
```bash
# バックエンド起動
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# フロントエンド起動
cd frontend
npm install
npm run dev
```

## ライセンス

MIT License

## 貢献

Issue、Pull Requestを歓迎します。

## 作者

FarBrain Development Team
