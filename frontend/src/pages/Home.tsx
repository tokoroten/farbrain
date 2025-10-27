/**
 * Home page - User registration and name input
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { api } from '../lib/api';
import { Button, Card } from '../components/common';
import theme from '../styles/theme';

export const Home = () => {
  const navigate = useNavigate();
  const { userId, userName, setUser } = useUserStore();
  const [name, setName] = useState(userName || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  // Check backend connection on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await api.health();
        setBackendConnected(true);
      } catch (err) {
        console.error('Backend health check failed:', err);
        setBackendConnected(false);
      }
    };
    checkBackend();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('名前を入力してください');
      return;
    }

    setIsLoading(true);

    try {
      // Generate user_id if not exists
      let currentUserId = userId;
      if (!currentUserId) {
        const response = await api.users.register({ name: name.trim() });
        currentUserId = response.user_id;
      }

      // Save to store
      setUser(currentUserId, name.trim());

      // Navigate to session list
      navigate('/sessions');
    } catch (err) {
      console.error('Failed to register user:', err);
      setError('登録に失敗しました。もう一度お試しください。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      ...theme.layout.flexCenter,
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{
        padding: theme.spacing['3xl'],
        boxShadow: theme.shadows.xl,
        maxWidth: '600px',
        width: '90%',
        margin: '0 auto',
      }}>
        {/* Backend Connection Error */}
        {backendConnected === false && (
          <div style={{
            padding: theme.spacing.md,
            marginBottom: theme.spacing.xl,
            background: '#ffebee',
            border: `1px solid ${theme.colors.error}`,
            borderRadius: theme.borderRadius.md,
            color: theme.colors.error,
            display: 'flex',
            alignItems: 'center',
            gap: theme.spacing.sm,
          }}>
            <span style={{ fontSize: theme.fontSize.lg }}>✗</span>
            <span>
              バックエンドに接続できません。サーバーが起動しているか確認してください。
            </span>
          </div>
        )}

        <h1 style={{
          fontSize: theme.fontSize['3xl'],
          fontWeight: 'bold',
          marginBottom: theme.spacing.sm,
          textAlign: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          FarBrain
        </h1>
        <p style={{
          textAlign: 'center',
          color: theme.colors.textLight,
          marginBottom: theme.spacing['2xl'],
        }}>
          LLM活用ゲーミフィケーションブレストツール
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: theme.spacing.xl }}>
            <label
              htmlFor="name"
              style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '600',
                color: theme.colors.text,
              }}
            >
              あなたの名前を入力してください
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="名前"
              maxLength={100}
              disabled={isLoading}
              style={{
                ...theme.components.input.base,
                border: `2px solid ${theme.colors.border}`,
              }}
              onFocus={(e) => e.target.style.borderColor = theme.colors.primary}
              onBlur={(e) => e.target.style.borderColor = theme.colors.border}
            />
            <p style={{
              ...theme.typography.small,
              marginTop: theme.spacing.sm,
            }}>
              セッション内で他の参加者に表示されます
            </p>
          </div>

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
            disabled={isLoading || !name.trim()}
            fullWidth
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              fontSize: theme.fontSize.lg,
              padding: theme.spacing.md,
              opacity: isLoading || !name.trim() ? 0.6 : 1,
            }}
          >
            {isLoading ? '処理中...' : '続ける'}
          </Button>
        </form>

        <div style={{
          marginTop: theme.spacing['2xl'],
          paddingTop: theme.spacing.xl,
          borderTop: `1px solid ${theme.colors.border}`,
          textAlign: 'center',
        }}>
          <button
            onClick={() => navigate('/admin')}
            style={{
              background: 'none',
              border: 'none',
              color: theme.colors.primary,
              cursor: 'pointer',
              fontSize: theme.fontSize.base,
              textDecoration: 'underline',
            }}
          >
            管理者ページ
          </button>
        </div>
      </Card>
    </div>
  );
};
