# 権限管理システム設計（RBAC）

## 現在の問題点
- Admin（管理者）と非Admin（一般ユーザー）の2段階のみ
- 細かい権限制御ができない
- 複数の管理者役割を分離できない

## 提案：ロールベースアクセス制御（RBAC）

### ロール定義

#### 1. Super Admin（スーパー管理者）
**できること：**
- ✅ 全ての操作が可能
- システム設定の変更
- ユーザーのロール変更
- デバッグ機能へのアクセス

#### 2. Session Manager（セッション管理者）
**できること：**
- ✅ セッションの作成・編集・削除
- ✅ セッション設定の変更
- ✅ セッションの開始・終了
- ❌ ユーザー管理
- ❌ デバッグ機能

**想定ユーザー：** プロジェクトマネージャー、ファシリテーター

#### 3. Moderator（モデレーター）
**できること：**
- ✅ 不適切なアイデアの削除
- ✅ セッション参加
- ✅ レポート生成
- ❌ セッション作成・編集
- ❌ ユーザー管理

**想定ユーザー：** ワークショップの運営サポート

#### 4. Analyst（アナリスト）
**できること：**
- ✅ レポート生成（Markdown/PDF）
- ✅ クラスタリングの強制実行
- ✅ データのエクスポート
- ✅ セッション参加（閲覧のみ）
- ❌ アイデアの削除
- ❌ セッション編集

**想定ユーザー：** データ分析担当者

#### 5. Participant（参加者）
**できること：**
- ✅ セッションへの参加
- ✅ アイデアの投稿
- ✅ 投票
- ✅ 対話モードの使用
- ❌ セッション管理
- ❌ 他人のアイデア削除

**想定ユーザー：** 一般ユーザー

---

## 権限マトリックス

| 機能 | Super Admin | Session Manager | Moderator | Analyst | Participant |
|-----|-------------|-----------------|-----------|---------|-------------|
| **セッション管理** |
| セッション作成 | ✅ | ✅ | ❌ | ❌ | ❌ |
| セッション編集 | ✅ | ✅ | ❌ | ❌ | ❌ |
| セッション削除 | ✅ | ✅ | ❌ | ❌ | ❌ |
| セッション参加 | ✅ | ✅ | ✅ | ✅ | ✅ |
| セッション開始/終了 | ✅ | ✅ | ❌ | ❌ | ❌ |
| **アイデア管理** |
| アイデア投稿 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 自分のアイデア削除 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 他人のアイデア削除 | ✅ | ✅ | ✅ | ❌ | ❌ |
| アイデア閲覧 | ✅ | ✅ | ✅ | ✅ | ✅ |
| **投票** |
| 投票 | ✅ | ✅ | ✅ | ❌ | ✅ |
| **レポート** |
| レポート生成 | ✅ | ✅ | ✅ | ✅ | ❌ |
| データエクスポート | ✅ | ✅ | ❌ | ✅ | ❌ |
| **ユーザー管理** |
| ユーザー一覧閲覧 | ✅ | ❌ | ❌ | ❌ | ❌ |
| ロール変更 | ✅ | ❌ | ❌ | ❌ | ❌ |
| **システム** |
| クラスタリング強制実行 | ✅ | ❌ | ❌ | ✅ | ❌ |
| デバッグ機能 | ✅ | ❌ | ❌ | ❌ | ❌ |
| システム設定 | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## データベーススキーマ

### 新テーブル: `roles`
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'super_admin', 'session_manager', 'moderator', 'analyst', 'participant'
    display_name VARCHAR(100) NOT NULL, -- 表示名（日本語）
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 新テーブル: `permissions`
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'session.create', 'idea.delete.any', etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 新テーブル: `role_permissions`（ロールと権限の関連付け）
```sql
CREATE TABLE role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

### 既存テーブル `users` を更新
```sql
ALTER TABLE users ADD COLUMN role_id INTEGER REFERENCES roles(id) DEFAULT 5;  -- デフォルトは 'participant'
ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT FALSE;  -- 後方互換性のため残す（非推奨）
```

---

## 権限チェックの実装

### バックエンド: デコレーター方式

```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    """権限チェック用デコレーター"""
    async def permission_checker(user_id: str = Depends(get_current_user)):
        if not await check_user_permission(user_id, permission):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user_id
    return permission_checker

# 使用例
@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(require_permission("session.delete"))
):
    # セッション削除処理
    pass
```

### 権限一覧

```python
# permissions.py
PERMISSIONS = {
    # セッション管理
    "session.create": "セッションを作成",
    "session.edit": "セッションを編集",
    "session.delete": "セッションを削除",
    "session.manage": "セッションを管理（開始/終了）",

    # アイデア管理
    "idea.create": "アイデアを投稿",
    "idea.delete.own": "自分のアイデアを削除",
    "idea.delete.any": "任意のアイデアを削除",

    # 投票
    "vote.cast": "投票する",

    # レポート
    "report.generate": "レポートを生成",
    "data.export": "データをエクスポート",

    # ユーザー管理
    "user.list": "ユーザー一覧を閲覧",
    "user.manage_roles": "ユーザーのロールを変更",

    # システム
    "clustering.force": "クラスタリングを強制実行",
    "debug.access": "デバッグ機能にアクセス",
    "system.configure": "システム設定を変更",
}
```

---

## フロントエンド: 権限による表示制御

```typescript
// usePermissions.ts
export function usePermissions() {
  const { user } = useAuth();

  const hasPermission = (permission: string): boolean => {
    return user?.permissions?.includes(permission) ?? false;
  };

  return { hasPermission };
}

// 使用例
function AdminPage() {
  const { hasPermission } = usePermissions();

  return (
    <div>
      {hasPermission('session.create') && (
        <button>新規セッション作成</button>
      )}
      {hasPermission('user.manage_roles') && (
        <button>ユーザー管理</button>
      )}
    </div>
  );
}
```

---

## 移行戦略

### Phase 1: データベース準備
1. ロール・権限テーブルを作成
2. デフォルトロールを挿入
3. 既存ユーザーにロールを割り当て

### Phase 2: バックエンド実装
1. 権限チェック機能を実装
2. 既存エンドポイントに権限チェックを追加
3. 後方互換性を保つ（is_adminフラグも残す）

### Phase 3: フロントエンド実装
1. 権限情報をログイン時に取得
2. UIを権限に基づいて表示/非表示
3. 管理画面でロール管理機能を追加

### Phase 4: 本番移行
1. 既存管理者にSuper Adminロールを付与
2. is_adminフラグを非推奨化
3. ドキュメント更新

---

## この設計のメリット

1. **柔軟性**: 新しいロールや権限を簡単に追加可能
2. **セキュリティ**: 最小権限の原則に基づいた設計
3. **拡張性**: 将来的にセッション単位の権限管理も可能
4. **後方互換**: 既存のis_adminフラグを残して段階的移行

---

## 次のステップ

この設計でよろしいですか？以下の点について確認させてください：

1. **ロールの種類**: 5種類で十分ですか？追加・削除したいロールはありますか？
2. **権限の細かさ**: 現在の権限粒度は適切ですか？
3. **実装優先度**: どの機能から実装を始めますか？
   - A. Session Manager（セッション管理者）
   - B. Moderator（モデレーター）
   - C. Analyst（アナリスト）
   - D. 全部一度に実装
