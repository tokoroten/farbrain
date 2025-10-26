/**
 * Scoreboard component showing user rankings
 */

import { useState } from 'react';
import type { ScoreboardEntry, IdeaVisualization } from '../types/api';

interface Props {
  rankings: ScoreboardEntry[];
  currentUserId: string;
  myIdeas: IdeaVisualization[];
  allIdeas: IdeaVisualization[];
  onHoverIdea?: (ideaId: string | null) => void;
}

type TabType = 'scoreboard' | 'myIdeas';

export const Scoreboard = ({ rankings, currentUserId, myIdeas, allIdeas, onHoverIdea }: Props) => {
  const [activeTab, setActiveTab] = useState<TabType>('scoreboard');

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e0e0e0',
      }}>
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '1rem',
        }}>
          <button
            onClick={() => setActiveTab('scoreboard')}
            style={{
              flex: 1,
              padding: '0.5rem',
              background: activeTab === 'scoreboard' ? '#667eea' : '#f0f0f0',
              color: activeTab === 'scoreboard' ? 'white' : '#666',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
            }}
          >
            🏆 スコアボード
          </button>
          <button
            onClick={() => setActiveTab('myIdeas')}
            style={{
              flex: 1,
              padding: '0.5rem',
              background: activeTab === 'myIdeas' ? '#667eea' : '#f0f0f0',
              color: activeTab === 'myIdeas' ? 'white' : '#666',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
            }}
          >
            💡 自分のアイディア ({myIdeas.length})
          </button>
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        minHeight: 0,
        maxHeight: '100%',
      }}>
        {activeTab === 'scoreboard' ? (
          // Scoreboard view
          rankings.length === 0 ? (
            <div style={{
              textAlign: 'center',
              color: '#666',
              padding: '2rem',
            }}>
              まだアイディアがありません
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {rankings.map((entry) => {
                const isCurrentUser = entry.user_id === currentUserId;
                const medalEmoji = entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : '';

                return (
                  <div
                    key={entry.user_id}
                    style={{
                      padding: '1rem',
                      background: isCurrentUser ? '#f0f7ff' : '#fafafa',
                      border: isCurrentUser ? '2px solid #667eea' : '1px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      transition: 'transform 0.2s',
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.5rem',
                    }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                      }}>
                        <span style={{
                          fontSize: '1.25rem',
                          fontWeight: 'bold',
                          color: entry.rank <= 3 ? '#667eea' : '#666',
                        }}>
                          #{entry.rank} {medalEmoji}
                        </span>
                        <span style={{
                          fontWeight: isCurrentUser ? 'bold' : 'normal',
                        }}>
                          {entry.user_name}
                          {isCurrentUser && (
                            <span style={{
                              marginLeft: '0.5rem',
                              fontSize: '0.875rem',
                              color: '#667eea',
                            }}>
                              (あなた)
                            </span>
                          )}
                        </span>
                      </div>
                      <div style={{
                        fontSize: '1.25rem',
                        fontWeight: 'bold',
                        color: '#667eea',
                      }}>
                        {entry.total_score.toFixed(1)}
                      </div>
                    </div>

                    <div style={{
                      display: 'flex',
                      gap: '1rem',
                      fontSize: '0.875rem',
                      color: '#666',
                      marginBottom: '0.5rem',
                    }}>
                      <span>💡 {entry.idea_count}件</span>
                      <span>📊 平均 {entry.avg_novelty_score.toFixed(1)}</span>
                    </div>

                    {entry.top_idea && (
                      <div style={{
                        padding: '0.5rem',
                        background: 'white',
                        borderRadius: '0.25rem',
                        fontSize: '0.875rem',
                      }}>
                        <div style={{
                          color: '#666',
                          marginBottom: '0.25rem',
                        }}>
                          最高スコア: {entry.top_idea.novelty_score.toFixed(1)}
                        </div>
                        <div style={{
                          color: '#333',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}>
                          {entry.top_idea.formatted_text}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )
        ) : (
          // My Ideas view
          myIdeas.length === 0 ? (
            <div style={{
              textAlign: 'center',
              color: '#666',
              padding: '2rem',
            }}>
              まだアイディアを投稿していません
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {myIdeas
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .map((idea, index) => {
                  // Find the closest idea if it exists
                  const closestIdea = idea.closest_idea_id
                    ? allIdeas.find(i => i.id === idea.closest_idea_id)
                    : null;

                  return (
                    <div
                      key={idea.id}
                      style={{
                        padding: '1rem',
                        background: '#fafafa',
                        border: '1px solid #e0e0e0',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                      onMouseEnter={() => onHoverIdea?.(idea.id)}
                      onMouseLeave={() => onHoverIdea?.(null)}
                    >
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'start',
                        marginBottom: '0.5rem',
                      }}>
                        <div style={{
                          fontSize: '0.875rem',
                          color: '#666',
                        }}>
                          #{index + 1}
                        </div>
                        <div style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '9999px',
                          background: `hsl(${idea.novelty_score * 1.2}, 70%, 85%)`,
                          fontSize: '0.875rem',
                          fontWeight: '600',
                        }}>
                          スコア: {idea.novelty_score.toFixed(1)}
                        </div>
                      </div>

                      <div style={{
                        marginBottom: '0.5rem',
                        fontSize: '0.95rem',
                        lineHeight: '1.5',
                      }}>
                        {idea.formatted_text}
                      </div>

                      <div style={{
                        display: 'flex',
                        gap: '1rem',
                        fontSize: '0.75rem',
                        color: '#999',
                        marginBottom: closestIdea ? '0.5rem' : '0',
                      }}>
                        <span>
                          {idea.cluster_id !== null ? `クラスタ: ${idea.cluster_id}` : 'クラスタ未割当'}
                        </span>
                        <span>
                          座標: ({idea.x.toFixed(2)}, {idea.y.toFixed(2)})
                        </span>
                        <span>
                          {new Date(idea.timestamp).toLocaleString('ja-JP', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>

                      {closestIdea && (
                        <div style={{
                          padding: '0.75rem',
                          background: '#f0f7ff',
                          borderLeft: '3px solid #667eea',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                        }}>
                          <div style={{
                            color: '#667eea',
                            fontWeight: '600',
                            marginBottom: '0.25rem',
                          }}>
                            💡 最も近いアイディア:
                          </div>
                          <div style={{
                            color: '#555',
                            lineHeight: '1.4',
                          }}>
                            {closestIdea.formatted_text}
                          </div>
                          <div style={{
                            color: '#999',
                            fontSize: '0.7rem',
                            marginTop: '0.25rem',
                          }}>
                            投稿者: {closestIdea.user_name}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          )
        )}
      </div>
    </div>
  );
};
