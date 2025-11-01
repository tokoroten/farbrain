/**
 * Session join page - Enter password if needed and join session
 */

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { useSessionStore } from '../store/sessionStore';
import { api } from '../lib/api';
import type { Session } from '../types/api';

export const SessionJoin = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const { userId, userName } = useUserStore();
  const { savePassword, getPassword, setCurrentSession } = useSessionStore();

  const [session, setSession] = useState<Session | null>(null);
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId || !userName || !sessionId) {
      navigate('/');
      return;
    }

    fetchSession();
  }, [userId, userName, sessionId, navigate]);

  const fetchSession = async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const sessionData = await api.sessions.get(sessionId);
      setSession(sessionData);

      // Try to join automatically if we have saved password
      if (sessionData.has_password) {
        const savedPassword = getPassword(sessionId);
        if (savedPassword) {
          setPassword(savedPassword);
          // Auto-join with saved password
          await handleJoin(savedPassword);
        }
      } else {
        // No password needed, auto-join
        await handleJoin();
      }
    } catch (err) {
      console.error('Failed to fetch session:', err);
      setError('セッションの取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoin = async (pwd?: string) => {
    if (!sessionId || !userId || !userName) return;

    setIsJoining(true);
    setError(null);

    try {
      await api.users.join(sessionId, {
        user_id: userId,
        name: userName,
        password: pwd || password || undefined,
      });

      // Save password if provided
      if (pwd || password) {
        savePassword(sessionId, pwd || password);
      }

      // Set current session
      setCurrentSession(sessionId);

      // Navigate to session
      navigate(`/session/${sessionId}`);
    } catch (err: any) {
      console.error('Failed to join session:', err);
      if (err.response?.status === 401) {
        setError('パスワードが正しくありません');
      } else {
        setError('セッションへの参加に失敗しました');
      }
    } finally {
      setIsJoining(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleJoin();
  };

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}>
        <div style={{ color: 'white', fontSize: '1.25rem' }}>
          読み込み中...
        </div>
      </div>
    );
  }

  if (!session) {
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
          textAlign: 'center',
          maxWidth: '500px',
          width: '90%',
        }}>
          <p style={{ color: '#c33', marginBottom: '1.5rem', fontSize: '1.1rem' }}>
            セッションが見つかりませんでした
          </p>
          <button
            onClick={() => navigate('/sessions')}
            style={{
              padding: '0.875rem 1.5rem',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '1rem',
            }}
          >
            セッション一覧に戻る
          </button>
        </div>
      </div>
    );
  }

  // If password is not required or already joining, show loading
  if (!session.has_password && isJoining) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}>
        <div style={{ color: 'white', fontSize: '1.25rem' }}>
          セッションに参加中...
        </div>
      </div>
    );
  }

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
          fontSize: '1.75rem',
          fontWeight: 'bold',
          marginBottom: '0.5rem',
        }}>
          {session.title}
        </h1>

        {session.description && (
          <p style={{
            color: '#666',
            marginBottom: '1rem',
          }}>
            {session.description}
          </p>
        )}

        <div style={{
          display: 'flex',
          gap: '1rem',
          marginBottom: '2rem',
          fontSize: '0.95rem',
          color: '#666',
        }}>
          <div>👥 {session.participant_count}人参加中</div>
          <div>💡 {session.idea_count}件のアイディア</div>
        </div>

        {session.has_password && (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
              }}>
                🔒 パスワード
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="セッションのパスワードを入力"
                disabled={isJoining}
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
              disabled={isJoining || !password}
              style={{
                width: '100%',
                padding: '0.875rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1.1rem',
                fontWeight: '600',
                cursor: isJoining || !password ? 'not-allowed' : 'pointer',
                opacity: isJoining || !password ? 0.6 : 1,
                marginBottom: '1rem',
              }}
            >
              {isJoining ? '参加中...' : 'セッションに参加'}
            </button>
          </form>
        )}

        <button
          onClick={() => navigate('/sessions')}
          style={{
            width: '100%',
            padding: '0.75rem',
            background: 'white',
            color: '#667eea',
            border: '2px solid #667eea',
            borderRadius: '0.5rem',
            cursor: 'pointer',
            fontWeight: '600',
          }}
        >
          戻る
        </button>
      </div>
    </div>
  );
};
