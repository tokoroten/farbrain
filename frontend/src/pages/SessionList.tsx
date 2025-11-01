/**
 * Session list page - Browse and join active sessions
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { api } from '../lib/api';
import type { Session } from '../types/api';

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
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>読み込み中...</div>
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
        maxWidth: '1400px',
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
            marginBottom: '0.5rem',
          }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              セッション一覧
            </h1>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
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
                  fontSize: '0.9rem',
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
                  fontSize: '0.9rem',
                }}
              >
                すべて
              </button>
            </div>
          </div>
          <p style={{ color: '#666' }}>
            ようこそ、{userName}さん
          </p>
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

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1.5rem',
          justifyContent: 'center',
        }}>
          {sessions.length === 0 ? (
            <div style={{
              background: 'white',
              padding: '3rem',
              borderRadius: '1rem',
              textAlign: 'center',
              gridColumn: '1 / -1',
            }}>
              <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '1.1rem' }}>
                セッションがまだ作成されていません
              </p>
              <button
                onClick={() => navigate('/admin')}
                style={{
                  padding: '1rem 2rem',
                  background: '#667eea',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  transition: 'background 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#5568d3';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#667eea';
                }}
              >
                プロジェクトを作成（管理者）
              </button>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                style={{
                  background: 'white',
                  padding: '1.5rem',
                  borderRadius: '1rem',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                  transition: 'transform 0.2s',
                  cursor: 'pointer',
                }}
                onClick={() => handleJoinSession(session.id)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'start',
                  marginBottom: '1rem',
                }}>
                  <h3 style={{
                    fontSize: '1.25rem',
                    fontWeight: 'bold',
                    marginBottom: '0.5rem',
                  }}>
                    {session.title}
                  </h3>
                  <span style={{
                    padding: '0.25rem 0.75rem',
                    borderRadius: '9999px',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    background: session.status === 'active' ? '#d4edda' : '#f8d7da',
                    color: session.status === 'active' ? '#155724' : '#721c24',
                  }}>
                    {session.status === 'active' ? 'アクティブ' : '終了'}
                  </span>
                </div>

                {session.description && (
                  <p style={{
                    color: '#666',
                    marginBottom: '1rem',
                    fontSize: '0.95rem',
                  }}>
                    {session.description}
                  </p>
                )}

                <div style={{
                  display: 'flex',
                  gap: '1rem',
                  marginBottom: '1rem',
                  fontSize: '0.875rem',
                  color: '#666',
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
                    padding: '0.5rem',
                    background: '#fff3cd',
                    borderRadius: '0.25rem',
                    fontSize: '0.875rem',
                    color: '#856404',
                    marginBottom: '0.5rem',
                  }}>
                    現在アイディアを受付していません
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
