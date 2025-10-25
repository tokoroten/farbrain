/**
 * Scoreboard component showing user rankings
 */

import type { ScoreboardEntry } from '../types/api';

interface Props {
  rankings: ScoreboardEntry[];
  currentUserId: string;
}

export const Scoreboard = ({ rankings, currentUserId }: Props) => {
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
        <h2 style={{
          fontSize: '1.25rem',
          fontWeight: 'bold',
        }}>
          🏆 スコアボード
        </h2>
      </div>

      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '1rem',
      }}>
        {rankings.length === 0 ? (
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
        )}
      </div>
    </div>
  );
};
