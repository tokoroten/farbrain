/**
 * Main brainstorming session page
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useUserStore } from '../store/userStore';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../lib/api';
import { VisualizationCanvas } from '../components/VisualizationCanvas';
import { Scoreboard } from '../components/Scoreboard';
import { IdeaInput } from '../components/IdeaInput';
import type {
  Session,
  IdeaVisualization,
  ClusterData,
  ScoreboardEntry,
  WebSocketEvent,
} from '../types/api';

export const BrainstormSession = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { userId, userName } = useUserStore();
  const { currentSessionId } = useSessionStore();

  const [session, setSession] = useState<Session | null>(null);
  const [ideas, setIdeas] = useState<IdeaVisualization[]>([]);
  const [clusters, setClusters] = useState<ClusterData[]>([]);
  const [scoreboard, setScoreboard] = useState<ScoreboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIdea, setSelectedIdea] = useState<IdeaVisualization | null>(null);
  const [hoveredIdeaId, setHoveredIdeaId] = useState<string | null>(null);
  const [showAdminDialog, setShowAdminDialog] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [clusteringInProgress, setClusteringInProgress] = useState(false);
  const [clusterMode, setClusterMode] = useState<'auto' | 'fixed'>('auto');
  const [fixedClusterCount, setFixedClusterCount] = useState('');

  // WebSocket connection
  const { isConnected } = useWebSocket({
    sessionId: sessionId!,
    onMessage: handleWebSocketMessage,
  });

  useEffect(() => {
    if (!userId || !userName || !sessionId) {
      navigate('/');
      return;
    }

    if (currentSessionId !== sessionId) {
      navigate(`/session/${sessionId}/join`);
      return;
    }

    fetchSessionData();

    // Auto-refresh scoreboard every 10 seconds
    const scoreboardInterval = setInterval(async () => {
      if (sessionId) {
        try {
          const scoreboardData = await api.visualization.getScoreboard(sessionId);
          setScoreboard(scoreboardData.rankings);
        } catch (err) {
          console.error('Failed to refresh scoreboard:', err);
        }
      }
    }, 10000);

    return () => clearInterval(scoreboardInterval);
  }, [userId, userName, sessionId, currentSessionId, navigate]);

  const fetchSessionData = async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const [sessionData, vizData, scoreboardData] = await Promise.all([
        api.sessions.get(sessionId),
        api.visualization.get(sessionId),
        api.visualization.getScoreboard(sessionId),
      ]);

      setSession(sessionData);
      setIdeas(vizData.ideas);
      setClusters(vizData.clusters);
      setScoreboard(scoreboardData.rankings);
    } catch (err) {
      console.error('Failed to fetch session data:', err);
      setError('データの取得に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchVisualizationData = async () => {
    if (!sessionId) return;

    try {
      const vizData = await api.visualization.get(sessionId);
      setIdeas(vizData.ideas);
      setClusters(vizData.clusters);
      console.log('Visualization data refreshed (ideas and clusters only)');
    } catch (err) {
      console.error('Failed to refresh visualization data:', err);
    }
  };

  function handleWebSocketMessage(event: WebSocketEvent) {
    switch (event.type) {
      case 'idea_created':
        // If coordinates were recalculated (UMAP re-fit), refresh entire visualization
        if (event.data.coordinates_recalculated) {
          console.log('UMAP recalculation detected - refreshing all visualization data');
          fetchVisualizationData();
        } else {
          // Otherwise just add the new idea
          setIdeas((prev) => [...prev, event.data]);
        }
        break;

      case 'coordinates_updated':
        setIdeas((prev) =>
          prev.map((idea) => {
            const update = event.data.updates.find((u) => u.idea_id === idea.id);
            return update ? { ...idea, x: update.x, y: update.y, cluster_id: update.cluster_id } : idea;
          })
        );
        break;

      case 'clusters_updated':
        setClusters(event.data.clusters);
        break;

      case 'clusters_recalculated':
        // Refresh only visualization data (ideas and clusters) when clusters are recalculated
        console.log('Clusters recalculated - refreshing visualization only');
        fetchVisualizationData();
        break;

      case 'scoreboard_updated':
        setScoreboard(event.data.rankings);
        break;

      case 'session_status_changed':
        if (session) {
          setSession({
            ...session,
            status: event.data.status,
            accepting_ideas: event.data.accepting_ideas,
          });
        }
        break;

      case 'user_joined':
        // Optionally show notification
        console.log(`${event.data.user_name} joined the session`);
        break;
    }
  }

  const handleIdeaSubmit = async (rawText: string, skipFormatting?: boolean) => {
    if (!sessionId || !userId) return;

    try {
      await api.ideas.create({
        session_id: sessionId,
        user_id: userId,
        raw_text: rawText,
        skip_formatting: skipFormatting,
      });
      // Idea will be added via WebSocket
    } catch (err) {
      console.error('Failed to submit idea:', err);
      throw err;
    }
  };

  const handleRecalculateClick = () => {
    if (ideas.length < 10) {
      alert('クラスタ再計算にはアイディアが10件以上必要です');
      return;
    }
    setShowAdminDialog(true);
  };

  const handleAdminSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!sessionId) return;

    try {
      const result = await api.auth.verifyAdmin(adminPassword);
      if (!result.success) {
        setError('管理者認証に失敗しました');
        return;
      }

      setClusteringInProgress(true);
      setShowAdminDialog(false);
      setAdminPassword('');

      // Prepare fixed_cluster_count parameter
      const fixedCount = clusterMode === 'fixed' && fixedClusterCount
        ? parseInt(fixedClusterCount, 10)
        : null;

      await api.debug.forceCluster(sessionId, true, fixedCount);

      setError(null);
      alert('クラスタリングが完了しました');
      await fetchSessionData();
    } catch (err) {
      console.error('Failed to recalculate clustering:', err);
      setError('クラスタリングの再計算に失敗しました');
    } finally {
      setClusteringInProgress(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
      }}>
        <div>読み込み中...</div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
      }}>
        <div>
          <p style={{ color: '#c33', marginBottom: '1rem' }}>{error || 'セッションが見つかりません'}</p>
          <button onClick={() => navigate('/sessions')}>戻る</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      height: '100vh',
      background: '#f5f5f5',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        background: 'white',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: '0.75rem 1rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>
            {session.title}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#666' }}>
            <span>💡 {ideas.length}件のアイディア</span>
            <span>👥 {session.participant_count}人参加中</span>
            <span style={{
              padding: '0.125rem 0.5rem',
              borderRadius: '0.25rem',
              background: isConnected ? '#d4edda' : '#f8d7da',
              color: isConnected ? '#155724' : '#721c24',
            }}>
              {isConnected ? '接続中' : '切断'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {ideas.length >= 10 && (
            <button
              onClick={handleRecalculateClick}
              disabled={clusteringInProgress}
              style={{
                padding: '0.5rem 1rem',
                background: clusteringInProgress ? '#ccc' : '#667eea',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: clusteringInProgress ? 'not-allowed' : 'pointer',
                fontWeight: '600',
              }}
            >
              {clusteringInProgress ? '再計算中...' : '🔄 クラスタ再計算（管理者）'}
            </button>
          )}
          <button
            onClick={() => navigate('/sessions')}
            style={{
              padding: '0.5rem 1rem',
              background: '#f0f0f0',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
            }}
          >
            セッション一覧
          </button>
        </div>
      </div>

      {/* Main content */}
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '1fr 320px',
        gap: '0.5rem',
        padding: '0.5rem',
        overflow: 'hidden',
        maxWidth: '100vw',
      }}>
        {/* Visualization + Input */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          minHeight: 0,
        }}>
          {/* Visualization */}
          <div style={{
            flex: 1,
            background: 'white',
            borderRadius: '0.5rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            overflow: 'hidden',
          }}>
            <VisualizationCanvas
              ideas={ideas}
              clusters={clusters}
              selectedIdea={selectedIdea}
              onSelectIdea={setSelectedIdea}
              hoveredIdeaId={hoveredIdeaId}
              currentUserId={userId || undefined}
            />
          </div>

          {/* Idea input */}
          {session.accepting_ideas && (
            <div style={{
              background: 'white',
              borderRadius: '0.5rem',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              padding: '1rem',
            }}>
              <IdeaInput onSubmit={handleIdeaSubmit} sessionId={sessionId} />
            </div>
          )}

          {!session.accepting_ideas && (
            <div style={{
              background: '#fff3cd',
              borderRadius: '0.5rem',
              padding: '1rem',
              textAlign: 'center',
              color: '#856404',
            }}>
              現在アイディアを受付していません
            </div>
          )}
        </div>

        {/* Scoreboard */}
        <div style={{
          background: 'white',
          borderRadius: '0.5rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          overflow: 'hidden',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}>
          <Scoreboard
            rankings={scoreboard}
            currentUserId={userId || ''}
            myIdeas={ideas.filter(idea => idea.user_id === userId)}
            allIdeas={ideas}
            onHoverIdea={setHoveredIdeaId}
          />
        </div>
      </div>

      {/* Selected idea modal */}
      {selectedIdea && (
        <div
          style={{
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
          }}
          onClick={() => setSelectedIdea(null)}
        >
          <div
            style={{
              background: 'white',
              padding: '2rem',
              borderRadius: '1rem',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'start',
              marginBottom: '1rem',
            }}>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>
                  {selectedIdea.user_name}
                </div>
                <div style={{
                  display: 'inline-block',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '9999px',
                  background: `hsl(${selectedIdea.novelty_score * 1.2}, 70%, 85%)`,
                  fontSize: '0.875rem',
                  fontWeight: '600',
                }}>
                  スコア: {selectedIdea.novelty_score.toFixed(1)}
                </div>
              </div>
              <button
                onClick={() => setSelectedIdea(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#666',
                }}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>
                整形後のアイディア
              </h3>
              <p style={{ fontSize: '1.1rem', lineHeight: '1.6' }}>
                {selectedIdea.formatted_text}
              </p>
            </div>

            <div>
              <h3 style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>
                元のテキスト
              </h3>
              <p style={{ color: '#666', fontSize: '0.95rem' }}>
                {selectedIdea.raw_text}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Admin authentication dialog */}
      {showAdminDialog && (
        <div
          style={{
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
          }}
          onClick={() => setShowAdminDialog(false)}
        >
          <div
            style={{
              background: 'white',
              padding: '2rem',
              borderRadius: '1rem',
              maxWidth: '400px',
              width: '90%',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem', fontWeight: 'bold' }}>
              クラスタ再計算設定
            </h2>
            <p style={{ marginBottom: '1.5rem', color: '#666' }}>
              クラスタ再計算には管理者パスワードが必要です
            </p>

            <form onSubmit={handleAdminSubmit}>
              <input
                type="password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="管理者パスワード"
                autoFocus
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '2px solid #e0e0e0',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  marginBottom: '1rem',
                  boxSizing: 'border-box',
                }}
              />

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.875rem' }}>
                  クラスタ数の設定
                </label>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', flex: 1 }}>
                    <input
                      type="radio"
                      name="clusterMode"
                      value="auto"
                      checked={clusterMode === 'auto'}
                      onChange={(e) => setClusterMode(e.target.value as 'auto' | 'fixed')}
                      style={{ marginRight: '0.5rem' }}
                    />
                    <span>自動 (計算式で決定)</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', flex: 1 }}>
                    <input
                      type="radio"
                      name="clusterMode"
                      value="fixed"
                      checked={clusterMode === 'fixed'}
                      onChange={(e) => setClusterMode(e.target.value as 'auto' | 'fixed')}
                      style={{ marginRight: '0.5rem' }}
                    />
                    <span>固定値</span>
                  </label>
                </div>
                {clusterMode === 'fixed' && (
                  <input
                    type="number"
                    min="2"
                    max="50"
                    value={fixedClusterCount}
                    onChange={(e) => setFixedClusterCount(e.target.value)}
                    placeholder="クラスタ数 (例: 5)"
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '2px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                    }}
                  />
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowAdminDialog(false);
                    setAdminPassword('');
                  }}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: '#f0f0f0',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    fontWeight: '600',
                  }}
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={!adminPassword.trim()}
                  style={{
                    flex: 1,
                    padding: '0.75rem',
                    background: adminPassword.trim() ? '#667eea' : '#ccc',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: adminPassword.trim() ? 'pointer' : 'not-allowed',
                    fontWeight: '600',
                  }}
                >
                  実行
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
