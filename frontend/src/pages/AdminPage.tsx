/**
 * Admin page - Create new brainstorming sessions
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { Button, Card } from '../components/common';
import theme from '../styles/theme';

export const AdminPage = () => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [selectedAction, setSelectedAction] = useState<'menu' | 'create' | 'test'>('menu');

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    duration: 7200,
    password: '',
    formatting_prompt: '',
    summarization_prompt: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isUnlimited, setIsUnlimited] = useState(false);

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
        duration: isUnlimited ? 999999999 : formData.duration,
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
        ...theme.layout.flexCenter,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}>
        <Card style={{
          padding: theme.spacing['3xl'],
          boxShadow: theme.shadows.xl,
          maxWidth: '800px',
          width: '90%',
        }}>
          <h1 style={{
            ...theme.typography.heading1,
            textAlign: 'center',
          }}>
            管理者認証
          </h1>
          <p style={{
            textAlign: 'center',
            color: theme.colors.textLight,
            marginBottom: theme.spacing['2xl'],
          }}>
            管理者パスワードを入力してください
          </p>

          <form onSubmit={handleAdminLogin}>
            <div style={{ marginBottom: theme.spacing.xl }}>
              <label
                htmlFor="adminPassword"
                style={{
                  display: 'block',
                  marginBottom: theme.spacing.sm,
                  fontWeight: '600',
                  color: theme.colors.text,
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
                  ...theme.components.input.base,
                  border: `2px solid ${theme.colors.border}`,
                }}
              />
            </div>

            {authError && (
              <div style={{
                padding: theme.spacing.md,
                marginBottom: theme.spacing.lg,
                background: '#fee2e2',
                border: `1px solid ${theme.colors.error}`,
                borderRadius: theme.borderRadius.md,
                color: theme.colors.error,
              }}>
                {authError}
              </div>
            )}

            <Button
              type="submit"
              disabled={isAuthLoading || !adminPassword.trim()}
              fullWidth
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                fontSize: theme.fontSize.lg,
                padding: theme.spacing.md,
                marginBottom: theme.spacing.lg,
                opacity: isAuthLoading || !adminPassword.trim() ? 0.6 : 1,
              }}
            >
              {isAuthLoading ? '確認中...' : 'ログイン'}
            </Button>

            <Button
              type="button"
              onClick={() => navigate('/sessions')}
              variant="secondary"
              fullWidth
              style={{
                padding: theme.spacing.md,
              }}
            >
              戻る
            </Button>
          </form>
        </Card>
      </div>
    );
  }

  // Show menu after authentication
  if (selectedAction === 'menu') {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: theme.spacing.lg,
      }}>
        <div style={{
          maxWidth: '1600px',
          margin: '0 auto',
        }}>
          <Card style={{
            padding: theme.spacing['2xl'],
          }}>
            <div style={{
              ...theme.layout.flexBetween,
              marginBottom: theme.spacing['2xl'],
            }}>
              <h1 style={theme.typography.heading1}>
                管理者メニュー
              </h1>
              <Button
                onClick={() => navigate('/')}
                variant="secondary"
                size="sm"
              >
                ホームへ戻る
              </Button>
            </div>

            {error && (
              <div style={{
                padding: theme.spacing.md,
                marginBottom: theme.spacing.xl,
                background: '#fee2e2',
                border: `1px solid ${theme.colors.error}`,
                borderRadius: theme.borderRadius.md,
                color: theme.colors.error,
              }}>
                {error}
              </div>
            )}

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '1.5rem',
            }}>
              {/* New Session Button */}
              <button
                onClick={() => setSelectedAction('create')}
                disabled={isLoading}
                style={{
                  padding: '2rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '1rem',
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                  textAlign: 'left',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 10px 30px rgba(102, 126, 234, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>➕</div>
                <div>新規セッション作成</div>
                <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '0.5rem' }}>
                  新しいブレインストーミングセッションを作成
                </div>
              </button>

              {/* Session Management Button */}
              <button
                onClick={() => navigate('/admin/sessions')}
                disabled={isLoading}
                style={{
                  padding: '2rem',
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '1rem',
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                  textAlign: 'left',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 10px 30px rgba(79, 172, 254, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🗑</div>
                <div>セッション管理</div>
                <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '0.5rem' }}>
                  セッションの削除・管理
                </div>
              </button>

              {/* Test Session Button */}
              <button
                onClick={handleCreateTestSession}
                disabled={isLoading}
                style={{
                  padding: '2rem',
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '1rem',
                  fontSize: '1.25rem',
                  fontWeight: '600',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.6 : 1,
                  textAlign: 'left',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!isLoading) {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 10px 30px rgba(240, 147, 251, 0.4)';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🧪</div>
                <div>{isLoading ? 'テストセッション作成中...' : 'テストセッション作成'}</div>
                <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '0.5rem' }}>
                  300個の多様なアイデアを含むテストセッションを自動生成
                </div>
              </button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: theme.spacing.lg,
    }}>
      <div style={{
        maxWidth: '1600px',
        margin: '0 auto',
      }}>
        <Card style={{
          padding: theme.spacing['2xl'],
        }}>
          <div style={{
            ...theme.layout.flexBetween,
            marginBottom: theme.spacing['2xl'],
          }}>
            <h1 style={theme.typography.heading1}>
              新規セッション作成
            </h1>
            <Button
              onClick={() => setSelectedAction('menu')}
              variant="secondary"
              size="sm"
            >
              戻る
            </Button>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: theme.spacing.xl }}>
              <label style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '600',
                color: theme.colors.text,
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
                  ...theme.components.input.base,
                  border: `2px solid ${theme.colors.border}`,
                }}
              />
            </div>

            <div style={{ marginBottom: theme.spacing.xl }}>
              <label style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '600',
                color: theme.colors.text,
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
                  ...theme.components.input.base,
                  border: `2px solid ${theme.colors.border}`,
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
                セッション時間
              </label>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                }}>
                  <input
                    type="checkbox"
                    checked={isUnlimited}
                    onChange={(e) => setIsUnlimited(e.target.checked)}
                    disabled={isLoading}
                    style={{
                      marginRight: '0.5rem',
                      width: '1.2rem',
                      height: '1.2rem',
                      cursor: 'pointer',
                    }}
                  />
                  <span style={{ fontWeight: '500' }}>時間無制限</span>
                </label>
              </div>

              {!isUnlimited && (
                <>
                  <input
                    type="number"
                    value={formData.duration}
                    onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) })}
                    min={60}
                    max={86400}
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
                  <p style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.5rem' }}>
                    秒数を入力（デフォルト: 7200秒 = 2時間）
                  </p>
                </>
              )}

              {isUnlimited && (
                <p style={{ fontSize: '0.875rem', color: '#667eea', marginTop: '0.5rem', fontWeight: '500' }}>
                  ✓ このセッションは時間制限なしで実行されます
                </p>
              )}
            </div>

            <div style={{ marginBottom: theme.spacing.xl }}>
              <label style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '600',
                color: theme.colors.text,
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
                  ...theme.components.input.base,
                  border: `2px solid ${theme.colors.border}`,
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
                padding: theme.spacing.md,
                marginBottom: theme.spacing.lg,
                background: '#fee2e2',
                border: `1px solid ${theme.colors.error}`,
                borderRadius: theme.borderRadius.md,
                color: theme.colors.error,
              }}>
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading || !formData.title.trim()}
              fullWidth
              style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                fontSize: theme.fontSize.lg,
                padding: theme.spacing.md,
                opacity: isLoading || !formData.title.trim() ? 0.6 : 1,
              }}
            >
              {isLoading ? '作成中...' : 'セッションを作成'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
};
