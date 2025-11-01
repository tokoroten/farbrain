/**
 * Home page - User registration and name input
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { api } from '../lib/api';

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
        {/* Backend Connection Error */}
        {backendConnected === false && (
          <div style={{
            padding: '0.75rem',
            marginBottom: '1.5rem',
            background: '#ffebee',
            border: '1px solid #ffcdd2',
            borderRadius: '0.5rem',
            color: '#c62828',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}>
            <span style={{ fontSize: '1.2rem' }}>✗</span>
            <span>
              バックエンドに接続できません。サーバーが起動しているか確認してください。
            </span>
          </div>
        )}

        <h1 style={{
          fontSize: '2.5rem',
          fontWeight: 'bold',
          marginBottom: '0.5rem',
          textAlign: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          FarBrain
        </h1>
        <p style={{
          textAlign: 'center',
          color: '#666',
          marginBottom: '2rem',
        }}>
          LLM活用ゲーミフィケーションブレストツール
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              htmlFor="name"
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: '600',
                color: '#333',
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
                width: '100%',
                padding: '0.75rem',
                border: '2px solid #e0e0e0',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                transition: 'border-color 0.2s',
                boxSizing: 'border-box',
              }}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
            />
            <p style={{
              fontSize: '0.875rem',
              color: '#666',
              marginTop: '0.5rem',
            }}>
              セッション内で他の参加者に表示されます
            </p>
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
            disabled={isLoading || !name.trim()}
            style={{
              width: '100%',
              padding: '0.875rem',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1.1rem',
              fontWeight: '600',
              cursor: isLoading || !name.trim() ? 'not-allowed' : 'pointer',
              opacity: isLoading || !name.trim() ? 0.6 : 1,
              transition: 'opacity 0.2s',
            }}
          >
            {isLoading ? '処理中...' : '続ける'}
          </button>
        </form>

        <div style={{
          marginTop: '2rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e0e0e0',
          textAlign: 'center',
        }}>
          <button
            onClick={() => navigate('/admin')}
            style={{
              background: 'none',
              border: 'none',
              color: '#667eea',
              cursor: 'pointer',
              fontSize: '0.95rem',
              textDecoration: 'underline',
            }}
          >
            管理者ページ
          </button>
        </div>
      </div>
    </div>
  );
};
