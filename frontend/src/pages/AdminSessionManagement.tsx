/**
 * Admin session management page - View and delete sessions
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Session } from '../types/api';

export const AdminSessionManagement = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active'>('all');
  const [deleteConfirmSessionId, setDeleteConfirmSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [exportingSessionId, setExportingSessionId] = useState<string | null>(null);

  // Edit session state
  const [editingSession, setEditingSession] = useState<Session | null>(null);
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    password: '',
    formatting_prompt: '',
    summarization_prompt: '',
  });
  const [isSaving, setIsSaving] = useState(false);

  // Admin authentication
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsAuthLoading(true);

    try {
      const result = await api.auth.verifyAdmin(adminPassword);
      if (result.success) {
        setIsAuthenticated(true);
      } else {
        setAuthError(result.message);
      }
    } catch (err) {
      console.error('Failed to verify admin password:', err);
      setAuthError('認証に失敗しました');
    } finally {
      setIsAuthLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchSessions();
    }
  }, [filter, isAuthenticated]);

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.sessions.list(filter === 'active');
      setSessions(response.sessions);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError('セッションの取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteClick = (sessionId: string) => {
    setDeleteConfirmSessionId(sessionId);
  };

  const handleConfirmDelete = async () => {
    if (!deleteConfirmSessionId) return;

    setDeletingSessionId(deleteConfirmSessionId);
    setError(null);

    try {
      await api.sessions.delete(deleteConfirmSessionId);
      await fetchSessions();
      setDeleteConfirmSessionId(null);
    } catch (err) {
      console.error('Failed to delete session:', err);
      setError('セッションの削除に失敗しました');
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleExport = async (sessionId: string) => {
    setExportingSessionId(sessionId);
    setError(null);

    try {
      await api.sessions.export(sessionId);
    } catch (err) {
      console.error('Failed to export session:', err);
      setError('CSVのエクスポートに失敗しました');
    } finally {
      setExportingSessionId(null);
    }
  };

  const handleEditClick = (session: Session) => {
    setEditingSession(session);
    setEditForm({
      title: session.title,
      description: session.description || '',
      password: '', // Don't pre-fill password for security
      formatting_prompt: session.formatting_prompt || '',
      summarization_prompt: session.summarization_prompt || '',
    });
  };

  const handleCancelEdit = () => {
    setEditingSession(null);
    setError(null);
  };

  const handleToggleAcceptingIdeas = async (sessionId: string, currentStatus: boolean) => {
    try {
      const newStatus = !currentStatus;

      // Update editingSession state immediately for instant UI feedback
      if (editingSession && editingSession.id === sessionId) {
        setEditingSession({
          ...editingSession,
          accepting_ideas: newStatus,
        });
      }

      await api.sessions.update(sessionId, {
        accepting_ideas: newStatus,
      });
      await fetchSessions();
    } catch (err) {
      console.error('Failed to toggle session status:', err);
      setError('セッションの状態変更に失敗しました');

      // Revert state on error
      if (editingSession && editingSession.id === sessionId) {
        setEditingSession({
          ...editingSession,
          accepting_ideas: currentStatus,
        });
      }
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSession) return;

    setIsSaving(true);
    setError(null);

    try {
      // Build update object with only non-empty values
      const updateData: any = {};
      if (editForm.title.trim()) updateData.title = editForm.title.trim();
      if (editForm.description.trim()) updateData.description = editForm.description.trim();
      if (editForm.password.trim()) updateData.password = editForm.password.trim();
      if (editForm.formatting_prompt.trim()) updateData.formatting_prompt = editForm.formatting_prompt.trim();
      if (editForm.summarization_prompt.trim()) updateData.summarization_prompt = editForm.summarization_prompt.trim();

      await api.sessions.update(editingSession.id, updateData);
      await fetchSessions();
      setEditingSession(null);
    } catch (err) {
      console.error('Failed to update session:', err);
      setError('セッションの更新に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  // Show password prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}>
        <div style={{
          background: 'white',
          padding: '3rem',
          borderRadius: '1rem',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          maxWidth: '800px',
          width: '90%',
        }}>
          <h1 style={{
            fontSize: '2rem',
            fontWeight: 'bold',
            marginBottom: '0.5rem',
            textAlign: 'center',
          }}>
            管理者認証
          </h1>
          <p style={{
            textAlign: 'center',
            color: '#666',
            marginBottom: '2rem',
          }}>
            セッション管理には管理者パスワードが必要です
          </p>

          <form onSubmit={handleAdminLogin}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label
                htmlFor="adminPassword"
                style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: '600',
                  color: '#333',
                }}
              >
                パスワード
              </label>
              <input
                id="adminPassword"
                type="password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="パスワード"
                disabled={isAuthLoading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '2px solid #e0e0e0',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            {authError && (
              <div style={{
                padding: '0.75rem',
                marginBottom: '1rem',
                background: '#fee',
                border: '1px solid #fcc',
                borderRadius: '0.5rem',
                color: '#c33',
              }}>
                {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={isAuthLoading || !adminPassword.trim()}
              style={{
                width: '100%',
                padding: '0.875rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1.1rem',
                fontWeight: '600',
                cursor: isAuthLoading || !adminPassword.trim() ? 'not-allowed' : 'pointer',
                opacity: isAuthLoading || !adminPassword.trim() ? 0.6 : 1,
                marginBottom: '1rem',
              }}
            >
              {isAuthLoading ? '確認中...' : 'ログイン'}
            </button>

            <button
              type="button"
              onClick={() => navigate('/admin')}
              style={{
                width: '100%',
                padding: '0.875rem',
                background: '#f0f0f0',
                color: '#333',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              戻る
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '1rem',
    }}>
      <div style={{
        maxWidth: '1600px',
        margin: '0 auto',
      }}>
        <div style={{
          background: 'white',
          padding: '2rem',
          borderRadius: '1rem',
          marginBottom: '2rem',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              セッション管理
            </h1>
            <button
              onClick={() => navigate('/admin')}
              style={{
                padding: '0.5rem 1rem',
                background: '#f0f0f0',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              戻る
            </button>
          </div>
          <p style={{ color: '#666' }}>
            セッションの表示と削除を管理
          </p>
        </div>

        <div style={{
          background: 'white',
          padding: '1rem',
          borderRadius: '1rem',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
        }}>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={() => setFilter('active')}
              style={{
                padding: '0.5rem 1rem',
                background: filter === 'active' ? '#667eea' : 'white',
                color: filter === 'active' ? 'white' : '#333',
                border: '1px solid #667eea',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              アクティブ
            </button>
            <button
              onClick={() => setFilter('all')}
              style={{
                padding: '0.5rem 1rem',
                background: filter === 'all' ? '#667eea' : 'white',
                color: filter === 'all' ? 'white' : '#333',
                border: '1px solid #667eea',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              すべて
            </button>
          </div>
          <button
            onClick={() => navigate('/admin')}
            style={{
              padding: '0.5rem 1rem',
              background: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            ➕ 新規セッション作成
          </button>
        </div>

        {error && (
          <div style={{
            background: '#fee',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            color: '#c33',
          }}>
            {error}
          </div>
        )}

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem', background: 'white', borderRadius: '1rem' }}>
            読み込み中...
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gap: '1rem',
          }}>
            {sessions.length === 0 ? (
              <div style={{
                background: 'white',
                padding: '3rem',
                borderRadius: '1rem',
                textAlign: 'center',
                color: '#666',
              }}>
                セッションがありません
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.id}
                  style={{
                    background: 'white',
                    padding: '1.5rem',
                    borderRadius: '1rem',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start',
                    gap: '1rem',
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
                          {session.title}
                        </h3>
                        <span style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          background: session.accepting_ideas ? '#d4edda' : '#f8d7da',
                          color: session.accepting_ideas ? '#155724' : '#721c24',
                        }}>
                          {session.accepting_ideas ? 'アクティブ' : '停止中'}
                        </span>
                      </div>

                      {session.description && (
                        <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.95rem' }}>
                          {session.description}
                        </p>
                      )}

                      <div style={{
                        display: 'flex',
                        gap: '1.5rem',
                        fontSize: '0.875rem',
                        color: '#666',
                      }}>
                        <div>👥 {session.participant_count}人</div>
                        <div>💡 {session.idea_count}件</div>
                        <div>📅 {new Date(session.created_at).toLocaleDateString('ja-JP')}</div>
                        {session.has_password && <div>🔒 パスワード保護</div>}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => handleEditClick(session)}
                        style={{
                          padding: '0.5rem 1rem',
                          background: '#667eea',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.5rem',
                          fontSize: '0.875rem',
                          cursor: 'pointer',
                          fontWeight: '600',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        ✏️ 編集
                      </button>
                      <button
                        onClick={() => handleExport(session.id)}
                        disabled={exportingSessionId === session.id}
                        style={{
                          padding: '0.5rem 1rem',
                          background: exportingSessionId === session.id ? '#ccc' : '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.5rem',
                          fontSize: '0.875rem',
                          cursor: exportingSessionId === session.id ? 'not-allowed' : 'pointer',
                          fontWeight: '600',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {exportingSessionId === session.id ? 'エクスポート中...' : '📥 CSV'}
                      </button>
                      <button
                        onClick={() => handleDeleteClick(session.id)}
                        disabled={deletingSessionId === session.id}
                        style={{
                          padding: '0.5rem 1rem',
                          background: deletingSessionId === session.id ? '#ccc' : '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.5rem',
                          fontSize: '0.875rem',
                          cursor: deletingSessionId === session.id ? 'not-allowed' : 'pointer',
                          fontWeight: '600',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {deletingSessionId === session.id ? '削除中...' : '🗑 削除'}
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Delete confirmation dialog */}
        {deleteConfirmSessionId && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}>
            <div style={{
              background: 'white',
              padding: '2rem',
              borderRadius: '1rem',
              maxWidth: '400px',
              width: '90%',
            }}>
              <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', fontWeight: 'bold' }}>
                セッションを削除
              </h2>
              <p style={{ marginBottom: '1.5rem', color: '#666' }}>
                このセッションと関連するすべてのデータ（ユーザー、アイデア、クラスタ）が削除されます。この操作は取り消せません。
              </p>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setDeleteConfirmSessionId(null)}
                  disabled={deletingSessionId !== null}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: '#f0f0f0',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: deletingSessionId !== null ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                  }}
                >
                  キャンセル
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDelete}
                  disabled={deletingSessionId !== null}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: deletingSessionId !== null ? '#ccc' : '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: deletingSessionId !== null ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                  }}
                >
                  {deletingSessionId !== null ? '削除中...' : '削除'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit session dialog */}
        {editingSession && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            overflowY: 'auto',
            padding: '1rem',
          }}>
            <div style={{
              background: 'white',
              padding: '2rem',
              borderRadius: '1rem',
              maxWidth: '600px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
            }}>
              <h2 style={{ marginBottom: '1.5rem', fontSize: '1.5rem', fontWeight: 'bold' }}>
                セッション編集
              </h2>

              <form onSubmit={handleEditSubmit}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    タイトル
                  </label>
                  <input
                    type="text"
                    value={editForm.title}
                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                    required
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    説明・コンテキスト
                  </label>
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                    }}
                    placeholder="セッションの目的やゴールを記述"
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    セッション状態
                  </label>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '0.75rem',
                    background: editingSession?.accepting_ideas ? '#d4edda' : '#f8d7da',
                    borderRadius: '0.5rem',
                    marginBottom: '0.5rem',
                  }}>
                    <span style={{
                      fontWeight: '600',
                      color: editingSession?.accepting_ideas ? '#155724' : '#721c24',
                    }}>
                      {editingSession?.accepting_ideas ? '✓ アイデア受付中' : '⏸ 停止中'}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => editingSession && handleToggleAcceptingIdeas(editingSession.id, editingSession.accepting_ideas)}
                    style={{
                      padding: '0.5rem 1rem',
                      background: editingSession?.accepting_ideas ? '#dc3545' : '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontWeight: '600',
                      fontSize: '0.875rem',
                    }}
                  >
                    {editingSession?.accepting_ideas ? '停止する' : '再開する'}
                  </button>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    パスワード（変更する場合のみ入力）
                  </label>
                  <input
                    type="password"
                    value={editForm.password}
                    onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                    }}
                    placeholder="空欄で変更なし"
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    アイデア整形プロンプト
                  </label>
                  <textarea
                    value={editForm.formatting_prompt}
                    onChange={(e) => setEditForm({ ...editForm, formatting_prompt: e.target.value })}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                    }}
                    placeholder="カスタム整形プロンプト（空欄でデフォルト）"
                  />
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    クラスタ要約プロンプト
                  </label>
                  <textarea
                    value={editForm.summarization_prompt}
                    onChange={(e) => setEditForm({ ...editForm, summarization_prompt: e.target.value })}
                    rows={3}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                    }}
                    placeholder="カスタム要約プロンプト（空欄でデフォルト）"
                  />
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    disabled={isSaving}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      background: '#f0f0f0',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: isSaving ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                    }}
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      background: isSaving ? '#ccc' : '#667eea',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: isSaving ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                    }}
                  >
                    {isSaving ? '保存中...' : '保存'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
