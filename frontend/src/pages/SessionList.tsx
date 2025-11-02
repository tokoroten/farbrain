/**
 * Session list page - Browse and join active sessions
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { api } from '../lib/api';
import type { Session } from '../types/api';
import styles from './SessionList.module.css';

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
      <div className={styles.loading}>
        <div>読み込み中...</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.header}>
          <div className={styles.headerTop}>
            <h1 className={styles.title}>
              セッション一覧
            </h1>
            <div className={styles.filterButtons}>
              <button
                onClick={() => setFilter('active')}
                className={`${styles.filterButton} ${filter === 'active' ? styles.active : ''}`}
              >
                アクティブ
              </button>
              <button
                onClick={() => setFilter('all')}
                className={`${styles.filterButton} ${filter === 'all' ? styles.active : ''}`}
              >
                すべて
              </button>
            </div>
          </div>
          <p className={styles.welcome}>
            ようこそ、{userName}さん
          </p>
        </div>

        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        <div className={styles.sessionsGrid}>
          {sessions.length === 0 ? (
            <div className={styles.emptyState}>
              <p className={styles.emptyMessage}>
                セッションがまだ作成されていません
              </p>
              <button
                onClick={() => navigate('/admin')}
                className={styles.createButton}
              >
                プロジェクトを作成（管理者）
              </button>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                className={styles.sessionCard}
                onClick={() => handleJoinSession(session.id)}
              >
                <div className={styles.sessionCardHeader}>
                  <h3 className={styles.sessionTitle}>
                    {session.title}
                  </h3>
                  <span className={`${styles.statusBadge} ${session.status === 'active' ? styles.active : styles.ended}`}>
                    {session.status === 'active' ? 'アクティブ' : '終了'}
                  </span>
                </div>

                {session.description && (
                  <p className={styles.sessionDescription}>
                    {session.description}
                  </p>
                )}

                <div className={styles.sessionMeta}>
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
                  <div className={styles.notAcceptingWarning}>
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
