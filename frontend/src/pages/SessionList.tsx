/**
 * Session list page - Browse and join active sessions
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { api } from '../lib/api';
import type { Session } from '../types/api';
import { Button, Card } from '../components/common';
import theme from '../styles/theme';

export const SessionList = () => {
  const navigate = useNavigate();
  const { userId, userName } = useUserStore();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active'>('active');

  useEffect(() => {
    if (!userId || !userName) {
      navigate('/');
      return;
    }

    fetchSessions();
  }, [userId, userName, navigate, filter]);

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

  const handleJoinSession = (sessionId: string) => {
    navigate(`/session/${sessionId}/join`);
  };

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', ...theme.layout.flexCenter }}>
        <div>読み込み中...</div>
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
        <Card style={{ padding: theme.spacing['2xl'], marginBottom: theme.spacing['2xl'] }}>
          <h1 style={theme.typography.heading1}>
            セッション一覧
          </h1>
          <p style={theme.typography.small}>
            ようこそ、{userName}さん
          </p>
        </Card>

        <Card style={{
          padding: theme.spacing.lg,
          marginBottom: theme.spacing.lg,
          display: 'flex',
          gap: theme.spacing.lg,
        }}>
          <Button
            onClick={() => setFilter('active')}
            variant={filter === 'active' ? 'primary' : 'secondary'}
            size="sm"
          >
            アクティブ
          </Button>
          <Button
            onClick={() => setFilter('all')}
            variant={filter === 'all' ? 'primary' : 'secondary'}
            size="sm"
          >
            すべて
          </Button>
        </Card>

        {error && (
          <Card style={{
            background: '#fee2e2',
            padding: theme.spacing.lg,
            marginBottom: theme.spacing.lg,
            color: theme.colors.error,
            border: `1px solid ${theme.colors.error}`,
          }}>
            {error}
          </Card>
        )}

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
          gap: '1.5rem',
        }}>
          {sessions.length === 0 ? (
            <Card style={{
              padding: theme.spacing['3xl'],
              textAlign: 'center',
              gridColumn: '1 / -1',
            }}>
              <p style={{
                ...theme.typography.body,
                color: theme.colors.textLight,
                marginBottom: theme.spacing.xl,
                fontSize: theme.fontSize.lg,
              }}>
                セッションがまだ作成されていません
              </p>
              <Button
                onClick={() => navigate('/admin')}
                variant="primary"
                size="lg"
              >
                プロジェクトを作成（管理者）
              </Button>
            </Card>
          ) : (
            sessions.map((session) => (
              <Card
                key={session.id}
                onClick={() => handleJoinSession(session.id)}
                hoverable
                style={{ padding: theme.spacing.xl }}
              >
                <div style={{
                  ...theme.layout.flexBetween,
                  alignItems: 'start',
                  marginBottom: theme.spacing.lg,
                }}>
                  <h3 style={theme.typography.heading3}>
                    {session.title}
                  </h3>
                  <span style={{
                    padding: `${theme.spacing.xs} ${theme.spacing.md}`,
                    borderRadius: theme.borderRadius.full,
                    fontSize: theme.fontSize.xs,
                    fontWeight: '600',
                    background: session.status === 'active' ? '#d4edda' : '#f8d7da',
                    color: session.status === 'active' ? '#155724' : '#721c24',
                  }}>
                    {session.status === 'active' ? 'アクティブ' : '終了'}
                  </span>
                </div>

                {session.description && (
                  <p style={{
                    ...theme.typography.body,
                    color: theme.colors.textLight,
                    marginBottom: theme.spacing.lg,
                  }}>
                    {session.description}
                  </p>
                )}

                <div style={{
                  display: 'flex',
                  gap: theme.spacing.lg,
                  marginBottom: theme.spacing.lg,
                  fontSize: theme.fontSize.sm,
                  color: theme.colors.textLight,
                }}>
                  <div>
                    👥 {session.participant_count}人
                  </div>
                  <div>
                    💡 {session.idea_count}件
                  </div>
                  {session.has_password && (
                    <div>🔒 パスワード保護</div>
                  )}
                </div>

                {!session.accepting_ideas && session.status === 'active' && (
                  <div style={{
                    padding: theme.spacing.sm,
                    background: '#fff3cd',
                    borderRadius: theme.borderRadius.sm,
                    fontSize: theme.fontSize.sm,
                    color: theme.colors.warning,
                    marginBottom: theme.spacing.sm,
                  }}>
                    現在アイディアを受付していません
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
