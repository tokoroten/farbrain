/**
 * Admin page - Create new brainstorming sessions
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Session } from '../types/api';

// Default prompts (matching backend defaults)
const DEFAULT_FORMATTING_PROMPT = `あなたはブレインストーミングセッションのファシリテーターです。
参加者の生のアイデアを、簡潔で具体的な形に整形するのがあなたの役割です。

整形の原則:
- 核心となるアイデアを明確に抽出する
- 具体的で実現可能な表現にする
- 感情的な表現を客観的に言い換える
- 1-2文で簡潔にまとめる
- 整形後のテキストのみを出力する(説明や前置きは不要)`;

const DEFAULT_SUMMARIZATION_PROMPT = `以下のアイディアに共通するテーマを1-3語で要約してください。
共通テーマ（1-3語のみ、説明不要）:`;

export const AdminPage = () => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    // Check if admin is already authenticated in this session
    return sessionStorage.getItem('adminAuthenticated') === 'true';
  });
  const [adminPassword, setAdminPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [selectedAction, setSelectedAction] = useState<'menu' | 'create' | 'test'>('menu');

  // Session management state
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [sessionFilter, setSessionFilter] = useState<'all' | 'active'>('all');
  const [deleteConfirmSessionId, setDeleteConfirmSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [exportingSessionId, setExportingSessionId] = useState<string | null>(null);
  const [editingSession, setEditingSession] = useState<Session | null>(null);
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    password: '',
    formatting_prompt: '',
    summarization_prompt: '',
  });
  const [isSaving, setIsSaving] = useState(false);

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    password: '',
    formatting_prompt: DEFAULT_FORMATTING_PROMPT,
    summarization_prompt: DEFAULT_SUMMARIZATION_PROMPT,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Fetch sessions when authenticated
  useEffect(() => {
    if (isAuthenticated && selectedAction === 'menu') {
      fetchSessions();
    }
  }, [isAuthenticated, sessionFilter, selectedAction]);

  const fetchSessions = async () => {
    setIsLoadingSessions(true);
    setError(null);

    try {
      const response = await api.sessions.list(sessionFilter === 'active');
      setSessions(response.sessions);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
      setError('セッションの取得に失敗しました');
    } finally {
      setIsLoadingSessions(false);
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
      password: '',
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

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setIsAuthLoading(true);

    try {
      const result = await api.auth.verifyAdmin(adminPassword);
      if (result.success) {
        setIsAuthenticated(true);
        // Save authentication state to sessionStorage
        sessionStorage.setItem('adminAuthenticated', 'true');
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.title.trim()) {
      setError('タイトルを入力してください');
      return;
    }

    setIsLoading(true);

    try {
      const session = await api.sessions.create({
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        password: formData.password || undefined,
        formatting_prompt: formData.formatting_prompt || undefined,
        summarization_prompt: formData.summarization_prompt || undefined,
      });

      // Navigate to the session
      navigate(`/session/${session.id}/join`);
    } catch (err) {
      console.error('Failed to create session:', err);
      setError('セッションの作成に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTestSession = async () => {
    setError(null);
    setIsLoading(true);

    try {
      const result = await api.debug.createTestSession();
      alert(`テストセッションを作成しました！\n\nタイトル: ${result.session_title}\nユーザー数: ${result.user_count}\nアイデア数: ${result.idea_count}\nクラスター数: ${result.cluster_count}`);
      // Navigate to the test session
      navigate(`/session/${result.session_id}/join`);
    } catch (err) {
      console.error('Failed to create test session:', err);
      setError('テストセッションの作成に失敗しました');
    } finally {
      setIsLoading(false);
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
          maxWidth: '500px',
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
            管理者パスワードを入力してください
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
              onClick={() => navigate('/sessions')}
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

  // Show menu after authentication
  if (selectedAction === 'menu') {
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
            padding: '1rem',
            borderRadius: '0.75rem',
            marginBottom: '1rem',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem',
            }}>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                管理者メニュー
              </h1>
              <button
                onClick={() => navigate('/')}
                style={{
                  padding: '0.4rem 0.8rem',
                  background: '#f0f0f0',
                  border: 'none',
                  borderRadius: '0.4rem',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                }}
              >
                ホームへ戻る
              </button>
            </div>

            {error && (
              <div style={{
                padding: '0.6rem',
                marginBottom: '1rem',
                background: '#fee',
                border: '1px solid #fcc',
                borderRadius: '0.4rem',
                color: '#c33',
                fontSize: '0.9rem',
              }}>
                {error}
              </div>
            )}

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '1rem',
            }}>
              {/* New Session Button */}
              <button
                onClick={() => setSelectedAction('create')}
                disabled={isLoading}
                style={{
                  padding: '1.25rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.75rem',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                  textAlign: 'left',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: '1.5rem', marginBottom: '0.3rem' }}>➕</div>
                <div>新規セッション作成</div>
                <div style={{ fontSize: '0.85rem', opacity: 0.9, marginTop: '0.3rem' }}>
                  新しいブレインストーミングセッションを作成
                </div>
              </button>

              {/* Test Session Button */}
              <button
                onClick={handleCreateTestSession}
                disabled={isLoading}
                style={{
                  padding: '1.25rem',
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.75rem',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                  textAlign: 'left',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(240, 147, 251, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: '1.5rem', marginBottom: '0.3rem' }}>🧪</div>
                <div>{isLoading ? 'テストセッション作成中...' : 'テストセッション作成'}</div>
                <div style={{ fontSize: '0.85rem', opacity: 0.9, marginTop: '0.3rem' }}>
                  300個の多様なアイデアを含むテストセッションを自動生成
                </div>
              </button>
            </div>
          </div>

          {/* Session List Section */}
          <div style={{
            background: 'white',
            padding: '0.75rem',
            borderRadius: '0.75rem',
          }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '0.75rem', paddingLeft: '0.25rem' }}>
              セッション一覧
            </h2>

            {isLoadingSessions ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#666', fontSize: '0.9rem' }}>
                読み込み中...
              </div>
            ) : sessions.length === 0 ? (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                color: '#666',
                fontSize: '0.9rem',
              }}>
                セッションがありません
              </div>
            ) : (
              <div style={{
                display: 'grid',
                gap: '0.75rem',
              }}>
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    style={{
                      padding: '1rem',
                      border: '1px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'start',
                      gap: '0.75rem',
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem' }}>
                          <h3 style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                            {session.title}
                          </h3>
                          <span style={{
                            padding: '0.2rem 0.6rem',
                            borderRadius: '9999px',
                            fontSize: '0.7rem',
                            fontWeight: '600',
                            background: session.accepting_ideas ? '#d4edda' : '#f8d7da',
                            color: session.accepting_ideas ? '#155724' : '#721c24',
                          }}>
                            {session.accepting_ideas ? 'アクティブ' : '停止中'}
                          </span>
                        </div>

                        {session.description && (
                          <p style={{ color: '#666', marginBottom: '0.6rem', fontSize: '0.85rem' }}>
                            {session.description}
                          </p>
                        )}

                        <div style={{
                          display: 'flex',
                          gap: '1rem',
                          fontSize: '0.8rem',
                          color: '#666',
                        }}>
                          <div>👥 {session.participant_count}人</div>
                          <div>💡 {session.idea_count}件</div>
                          <div>📅 {new Date(session.created_at).toLocaleDateString('ja-JP')}</div>
                          {session.has_password && <div>🔒 パスワード保護</div>}
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button
                          onClick={() => handleEditClick(session)}
                          style={{
                            padding: '0.4rem 0.75rem',
                            background: '#667eea',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.4rem',
                            fontSize: '0.8rem',
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
                            padding: '0.4rem 0.75rem',
                            background: exportingSessionId === session.id ? '#ccc' : '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.4rem',
                            fontSize: '0.8rem',
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
                            padding: '0.4rem 0.75rem',
                            background: deletingSessionId === session.id ? '#ccc' : '#dc3545',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.4rem',
                            fontSize: '0.8rem',
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
                ))}
              </div>
            )}
          </div>

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
                padding: '1.25rem',
                borderRadius: '0.75rem',
                maxWidth: '400px',
                width: '90%',
              }}>
                <h2 style={{ marginBottom: '0.75rem', fontSize: '1.25rem', fontWeight: 'bold' }}>
                  セッションを削除
                </h2>
                <p style={{ marginBottom: '1rem', color: '#666', fontSize: '0.9rem' }}>
                  このセッションと関連するすべてのデータ（ユーザー、アイデア、クラスタ）が削除されます。この操作は取り消せません。
                </p>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => setDeleteConfirmSessionId(null)}
                    disabled={deletingSessionId !== null}
                    style={{
                      flex: 1,
                      padding: '0.6rem',
                      background: '#f0f0f0',
                      border: 'none',
                      borderRadius: '0.4rem',
                      cursor: deletingSessionId !== null ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                      fontSize: '0.9rem',
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
                      padding: '0.6rem',
                      background: deletingSessionId !== null ? '#ccc' : '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.4rem',
                      cursor: deletingSessionId !== null ? 'not-allowed' : 'pointer',
                      fontWeight: '600',
                      fontSize: '0.9rem',
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
              padding: '0.75rem',
            }}>
              <div style={{
                background: 'white',
                padding: '1.25rem',
                borderRadius: '0.75rem',
                maxWidth: '600px',
                width: '100%',
                maxHeight: '90vh',
                overflowY: 'auto',
              }}>
                <h2 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 'bold' }}>
                  セッション編集
                </h2>

                <form onSubmit={handleEditSubmit}>
                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      タイトル
                    </label>
                    <input
                      type="text"
                      value={editForm.title}
                      onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                      required
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.4rem',
                        fontSize: '0.9rem',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>

                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      説明・コンテキスト
                    </label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      rows={2}
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.4rem',
                        fontSize: '0.9rem',
                        boxSizing: 'border-box',
                        resize: 'vertical',
                      }}
                      placeholder="セッションの目的やゴールを記述"
                    />
                  </div>

                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      セッション状態
                    </label>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.6rem',
                      background: editingSession?.accepting_ideas ? '#d4edda' : '#f8d7da',
                      borderRadius: '0.4rem',
                      marginBottom: '0.4rem',
                    }}>
                      <span style={{
                        fontWeight: '600',
                        fontSize: '0.85rem',
                        color: editingSession?.accepting_ideas ? '#155724' : '#721c24',
                      }}>
                        {editingSession?.accepting_ideas ? '✓ アイデア受付中' : '⏸ 停止中'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => editingSession && handleToggleAcceptingIdeas(editingSession.id, editingSession.accepting_ideas)}
                      style={{
                        padding: '0.4rem 0.75rem',
                        background: editingSession?.accepting_ideas ? '#dc3545' : '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.4rem',
                        cursor: 'pointer',
                        fontWeight: '600',
                        fontSize: '0.8rem',
                      }}
                    >
                      {editingSession?.accepting_ideas ? '停止する' : '再開する'}
                    </button>
                  </div>

                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      パスワード（変更する場合のみ入力）
                    </label>
                    <input
                      type="password"
                      value={editForm.password}
                      onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.4rem',
                        fontSize: '0.9rem',
                        boxSizing: 'border-box',
                      }}
                      placeholder="空欄で変更なし"
                    />
                  </div>

                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      アイデア整形プロンプト
                    </label>
                    <textarea
                      value={editForm.formatting_prompt}
                      onChange={(e) => setEditForm({ ...editForm, formatting_prompt: e.target.value })}
                      rows={2}
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.4rem',
                        fontSize: '0.85rem',
                        boxSizing: 'border-box',
                        resize: 'vertical',
                      }}
                      placeholder="カスタム整形プロンプト（空欄でデフォルト）"
                    />
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.9rem' }}>
                      クラスタ要約プロンプト
                    </label>
                    <textarea
                      value={editForm.summarization_prompt}
                      onChange={(e) => setEditForm({ ...editForm, summarization_prompt: e.target.value })}
                      rows={2}
                      style={{
                        width: '100%',
                        padding: '0.6rem',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.4rem',
                        fontSize: '0.85rem',
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
                        padding: '0.6rem',
                        background: '#f0f0f0',
                        border: 'none',
                        borderRadius: '0.4rem',
                        cursor: isSaving ? 'not-allowed' : 'pointer',
                        fontWeight: '600',
                        fontSize: '0.9rem',
                      }}
                    >
                      キャンセル
                    </button>
                    <button
                      type="submit"
                      disabled={isSaving}
                      style={{
                        flex: 1,
                        padding: '0.6rem',
                        background: isSaving ? '#ccc' : '#667eea',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.4rem',
                        cursor: isSaving ? 'not-allowed' : 'pointer',
                        fontWeight: '600',
                        fontSize: '0.9rem',
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
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '2rem 1rem',
    }}>
      <div style={{
        maxWidth: '900px',
        margin: '0 auto',
      }}>
        <div style={{
          background: 'white',
          padding: '2.5rem',
          borderRadius: '1rem',
          boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
          }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              新規セッション作成
            </h1>
            <button
              onClick={() => setSelectedAction('menu')}
              style={{
                padding: '0.5rem 1rem',
                background: '#f0f0f0',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
              }}
            >
              戻る
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
              }}>
                タイトル *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="例: 新規事業アイディア出し"
                maxLength={255}
                disabled={isLoading}
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

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
              }}>
                説明
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="セッションの目的や説明"
                rows={3}
                disabled={isLoading}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '2px solid #e0e0e0',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  boxSizing: 'border-box',
                  resize: 'vertical',
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
              }}>
                パスワード（オプション）
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                placeholder="空欄の場合はパスワード保護なし"
                disabled={isLoading}
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

            <div style={{ marginBottom: '1.5rem' }}>
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#667eea',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  textDecoration: 'underline',
                }}
              >
                {showAdvanced ? '詳細設定を隠す' : '詳細設定を表示'}
              </button>
            </div>

            {showAdvanced && (
              <>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{
                    display: 'block',
                    marginBottom: '0.5rem',
                    fontWeight: '600',
                  }}>
                    カスタムフォーマティングプロンプト
                  </label>
                  <textarea
                    value={formData.formatting_prompt}
                    onChange={(e) => setFormData({ ...formData, formatting_prompt: e.target.value })}
                    placeholder="LLMがアイディアを整形する際のカスタムプロンプト"
                    rows={4}
                    maxLength={2000}
                    disabled={isLoading}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '0.95rem',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                    }}
                  />
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{
                    display: 'block',
                    marginBottom: '0.5rem',
                    fontWeight: '600',
                  }}>
                    カスタム要約プロンプト
                  </label>
                  <textarea
                    value={formData.summarization_prompt}
                    onChange={(e) => setFormData({ ...formData, summarization_prompt: e.target.value })}
                    placeholder="クラスタラベルを生成する際のカスタムプロンプト"
                    rows={4}
                    maxLength={2000}
                    disabled={isLoading}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '0.95rem',
                      boxSizing: 'border-box',
                      resize: 'vertical',
                    }}
                  />
                </div>
              </>
            )}

            {error && (
              <div style={{
                padding: '0.75rem',
                marginBottom: '1rem',
                background: '#fee',
                border: '1px solid #fcc',
                borderRadius: '0.5rem',
                color: '#c33',
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !formData.title.trim()}
              style={{
                width: '100%',
                padding: '0.875rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1.1rem',
                fontWeight: '600',
                cursor: isLoading || !formData.title.trim() ? 'not-allowed' : 'pointer',
                opacity: isLoading || !formData.title.trim() ? 0.6 : 1,
              }}
            >
              {isLoading ? '作成中...' : 'セッションを作成'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
