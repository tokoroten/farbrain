/**
 * Scoreboard component showing user rankings
 */

import { useState } from 'react';
import type { ScoreboardEntry, IdeaVisualization, ClusterData } from '../types/api';
import { getUserColorFromId } from './VisualizationCanvas';

interface Props {
  rankings: ScoreboardEntry[];
  currentUserId: string;
  myIdeas: IdeaVisualization[];
  allIdeas: IdeaVisualization[];
  clusters: ClusterData[];
  onHoverIdea?: (ideaId: string | null) => void;
  onHoverUser?: (userId: string | null) => void;
  onDeleteIdea?: (ideaId: string, adminPassword?: string) => Promise<void>;
  onVoteIdea?: (ideaId: string) => Promise<void>;
  onUnvoteIdea?: (ideaId: string) => Promise<void>;
  onUserFilterChange?: (userId: string | null) => void;
}

type TabType = 'scoreboard' | 'myIdeas' | 'allIdeas';
type SortOrder = 'latest' | 'score' | 'upvote';

// Common idea card component
const IdeaCard = ({
  idea,
  index,
  allIdeas,
  clusters,
  currentUserId,
  onHoverIdea,
  showUserInfo = false,
  onDeleteIdea,
  onVoteIdea,
  onUnvoteIdea,
}: {
  idea: IdeaVisualization;
  index: number;
  allIdeas: IdeaVisualization[];
  clusters: ClusterData[];
  currentUserId: string;
  onHoverIdea?: (ideaId: string | null) => void;
  showUserInfo?: boolean;
  onDeleteIdea?: (ideaId: string, adminPassword?: string) => Promise<void>;
  onVoteIdea?: (ideaId: string) => Promise<void>;
  onUnvoteIdea?: (ideaId: string) => Promise<void>;
}) => {
  const isMyIdea = idea.user_id === currentUserId;
  const closestIdea = idea.closest_idea_id
    ? allIdeas.find(i => i.id === idea.closest_idea_id)
    : null;

  // Get cluster label
  const cluster = clusters.find(c => c.id === idea.cluster_id);
  const clusterLabel = cluster ? cluster.label : `クラスタ ${idea.cluster_id}`;

  return (
    <div
      style={{
        padding: '1rem',
        background: isMyIdea && showUserInfo ? '#f0f7ff' : '#fafafa',
        border: isMyIdea && showUserInfo ? '2px solid #667eea' : '1px solid #e0e0e0',
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
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem',
          color: '#666',
        }}>
          <span>#{index + 1}</span>
          {showUserInfo && (
            <>
              <div
                style={{
                  width: '14px',
                  height: '14px',
                  borderRadius: '50%',
                  background: getUserColorFromId(idea.user_id),
                  border: '2px solid white',
                  boxShadow: '0 0 0 1px rgba(0,0,0,0.1)',
                  flexShrink: 0,
                }}
                title={`${idea.user_name}の色`}
              />
              <span style={{ fontWeight: isMyIdea ? 'bold' : 'normal' }}>
                {idea.user_name}
                {isMyIdea && <span style={{ color: '#667eea' }}> (あなた)</span>}
              </span>
            </>
          )}
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}>
          <div style={{
            padding: '0.25rem 0.75rem',
            borderRadius: '9999px',
            background: `hsl(${idea.novelty_score * 1.2}, 70%, 85%)`,
            fontSize: '0.875rem',
            fontWeight: '600',
          }}>
            {showUserInfo ? idea.novelty_score.toFixed(1) : `スコア: ${idea.novelty_score.toFixed(1)}`}
          </div>
          {onVoteIdea && onUnvoteIdea && (
            <button
              onClick={async (e) => {
                e.stopPropagation();
                if (idea.user_has_voted) {
                  await onUnvoteIdea(idea.id);
                } else {
                  await onVoteIdea(idea.id);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.25rem 0.5rem',
                background: idea.user_has_voted ? '#667eea' : 'transparent',
                color: idea.user_has_voted ? 'white' : '#666',
                border: idea.user_has_voted ? 'none' : '1px solid #ccc',
                borderRadius: '9999px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: '600',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                if (!idea.user_has_voted) {
                  e.currentTarget.style.background = '#f0f0f0';
                }
              }}
              onMouseLeave={(e) => {
                if (!idea.user_has_voted) {
                  e.currentTarget.style.background = 'transparent';
                }
              }}
              title={idea.user_has_voted ? 'upvoteを取り消す' : 'upvoteする'}
            >
              <span>👍</span>
              <span>{idea.vote_count}</span>
            </button>
          )}
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
          {idea.cluster_id !== null ? clusterLabel : 'クラスタ未割当'}
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
            💡 投稿時に最も近かったアイディア:
          </div>
          <div style={{
            color: '#555',
            lineHeight: '1.4',
          }}>
            {closestIdea.formatted_text}
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            color: '#999',
            fontSize: '0.7rem',
            marginTop: '0.25rem',
          }}>
            <span>投稿者:</span>
            <div
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                background: getUserColorFromId(closestIdea.user_id),
                border: '1.5px solid white',
                boxShadow: '0 0 0 1px rgba(0,0,0,0.1)',
                flexShrink: 0,
              }}
              title={`${closestIdea.user_name}の色`}
            />
            <span>{closestIdea.user_name}</span>
          </div>
          {closestIdea.user_id === idea.user_id && (
            <div style={{
              color: '#ff6b6b',
              fontSize: '0.7rem',
              marginTop: '0.25rem',
              fontWeight: '600',
            }}>
              ⚠️ 同じユーザーのため減点（0.5倍）
            </div>
          )}
        </div>
      )}

      {/* Delete button */}
      {onDeleteIdea && (
        <div style={{ marginTop: '0.25rem', textAlign: 'right', lineHeight: 1 }}>
          {isMyIdea ? (
            <button
              onClick={async (e) => {
                e.stopPropagation();
                if (confirm('このアイディアを削除しますか？')) {
                  await onDeleteIdea(idea.id);
                }
              }}
              style={{
                background: 'transparent',
                color: '#ddd',
                border: 'none',
                padding: '0 0.25rem',
                cursor: 'pointer',
                fontSize: '0.65rem',
                transition: 'color 0.2s',
                opacity: 0.4,
                lineHeight: 1,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ff6b6b';
                e.currentTarget.style.opacity = '1';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#ddd';
                e.currentTarget.style.opacity = '0.4';
              }}
              title="削除"
            >
              delete
            </button>
          ) : (
            <button
              onClick={async (e) => {
                e.stopPropagation();
                const password = prompt('管理者パスワードを入力してください:');
                if (password) {
                  await onDeleteIdea(idea.id, password);
                }
              }}
              style={{
                background: 'transparent',
                color: '#ddd',
                border: 'none',
                padding: '0 0.25rem',
                cursor: 'pointer',
                fontSize: '0.65rem',
                transition: 'color 0.2s',
                opacity: 0.3,
                lineHeight: 1,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#999';
                e.currentTarget.style.opacity = '0.8';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#ddd';
                e.currentTarget.style.opacity = '0.3';
              }}
              title="管理者削除"
            >
              delete
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const Scoreboard = ({ rankings, currentUserId, myIdeas, allIdeas, clusters, onHoverIdea, onHoverUser, onDeleteIdea, onVoteIdea, onUnvoteIdea, onUserFilterChange }: Props) => {
  const [activeTab, setActiveTab] = useState<TabType>('scoreboard');
  const [sortOrder, setSortOrder] = useState<SortOrder>('latest');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  // Get unique users from all ideas
  const uniqueUsers = Array.from(
    new Map(allIdeas.map(idea => [idea.user_id, { id: idea.user_id, name: idea.user_name }])).values()
  ).sort((a, b) => a.name.localeCompare(b.name));

  // Filter and sort ideas based on current filters
  const getFilteredAndSortedIdeas = (ideas: IdeaVisualization[]) => {
    // Apply user filter
    let filtered = selectedUserId
      ? ideas.filter(idea => idea.user_id === selectedUserId)
      : ideas;

    // Apply sorting
    switch (sortOrder) {
      case 'latest':
        return filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      case 'score':
        return filtered.sort((a, b) => b.novelty_score - a.novelty_score);
      case 'upvote':
        return filtered.sort((a, b) => b.vote_count - a.vote_count);
      default:
        return filtered;
    }
  };

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
              fontSize: '0.75rem',
            }}
          >
            🏆 ランキング
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
              fontSize: '0.75rem',
            }}
          >
            💡 自分 ({myIdeas.length})
          </button>
          <button
            onClick={() => setActiveTab('allIdeas')}
            style={{
              flex: 1,
              padding: '0.5rem',
              background: activeTab === 'allIdeas' ? '#667eea' : '#f0f0f0',
              color: activeTab === 'allIdeas' ? 'white' : '#666',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.75rem',
            }}
          >
            🌐 全員 ({allIdeas.length})
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

                return (
                  <div
                    key={entry.user_id}
                    style={{
                      padding: '1rem',
                      background: isCurrentUser ? '#f0f7ff' : '#fafafa',
                      border: isCurrentUser ? '2px solid #667eea' : '1px solid #e0e0e0',
                      borderRadius: '0.5rem',
                      transition: 'transform 0.2s',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={() => onHoverUser?.(entry.user_id)}
                    onMouseLeave={() => onHoverUser?.(null)}
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
                          #{entry.rank}
                        </span>
                        <div
                          style={{
                            width: '16px',
                            height: '16px',
                            borderRadius: '50%',
                            background: getUserColorFromId(entry.user_id),
                            border: '2px solid white',
                            boxShadow: '0 0 0 1px rgba(0,0,0,0.1)',
                            flexShrink: 0,
                          }}
                          title={`${entry.user_name}の色`}
                        />
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
        ) : activeTab === 'myIdeas' ? (
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
                .map((idea, index) => (
                  <IdeaCard
                    key={idea.id}
                    idea={idea}
                    index={index}
                    allIdeas={allIdeas}
                    clusters={clusters}
                    currentUserId={currentUserId}
                    onHoverIdea={onHoverIdea}
                    showUserInfo={false}
                    onDeleteIdea={onDeleteIdea}
                    onVoteIdea={onVoteIdea}
                    onUnvoteIdea={onUnvoteIdea}
                  />
                ))}
            </div>
          )
        ) : (
          // All Ideas view
          allIdeas.length === 0 ? (
            <div style={{
              textAlign: 'center',
              color: '#666',
              padding: '2rem',
            }}>
              まだアイディアがありません
            </div>
          ) : (
            <>
              {/* Filter controls */}
              <div style={{
                display: 'flex',
                gap: '0.75rem',
                marginBottom: '1rem',
                flexWrap: 'wrap',
                alignItems: 'center',
              }}>
                {/* Sort buttons */}
                <div style={{
                  display: 'flex',
                  gap: '0.5rem',
                  flexWrap: 'wrap',
                }}>
                  <button
                    onClick={() => setSortOrder('latest')}
                    style={{
                      padding: '0.4rem 0.75rem',
                      background: sortOrder === 'latest' ? '#667eea' : '#f0f0f0',
                      color: sortOrder === 'latest' ? 'white' : '#666',
                      border: 'none',
                      borderRadius: '0.4rem',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                    }}
                  >
                    📅 最新
                  </button>
                  <button
                    onClick={() => setSortOrder('score')}
                    style={{
                      padding: '0.4rem 0.75rem',
                      background: sortOrder === 'score' ? '#667eea' : '#f0f0f0',
                      color: sortOrder === 'score' ? 'white' : '#666',
                      border: 'none',
                      borderRadius: '0.4rem',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                    }}
                  >
                    ⭐ 点数
                  </button>
                  <button
                    onClick={() => setSortOrder('upvote')}
                    style={{
                      padding: '0.4rem 0.75rem',
                      background: sortOrder === 'upvote' ? '#667eea' : '#f0f0f0',
                      color: sortOrder === 'upvote' ? 'white' : '#666',
                      border: 'none',
                      borderRadius: '0.4rem',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      transition: 'all 0.2s',
                    }}
                  >
                    👍 Upvote
                  </button>
                </div>

                {/* User filter dropdown */}
                <select
                  value={selectedUserId || ''}
                  onChange={(e) => {
                    const newUserId = e.target.value || null;
                    setSelectedUserId(newUserId);
                    onUserFilterChange?.(newUserId);
                    // Clear hover state when filter changes
                    onHoverUser?.(null);
                    onHoverIdea?.(null);
                  }}
                  style={{
                    padding: '0.4rem 0.75rem',
                    background: selectedUserId ? '#667eea' : '#f0f0f0',
                    color: selectedUserId ? 'white' : '#666',
                    border: 'none',
                    borderRadius: '0.4rem',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    transition: 'all 0.2s',
                  }}
                >
                  <option value="">👥 全員</option>
                  {uniqueUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {getFilteredAndSortedIdeas(allIdeas).map((idea, index) => (
                  <IdeaCard
                    key={idea.id}
                    idea={idea}
                    index={index}
                    allIdeas={allIdeas}
                    clusters={clusters}
                    currentUserId={currentUserId}
                    onHoverIdea={onHoverIdea}
                    showUserInfo={true}
                    onDeleteIdea={onDeleteIdea}
                    onVoteIdea={onVoteIdea}
                    onUnvoteIdea={onUnvoteIdea}
                  />
                ))}
              </div>
            </>
          )
        )}
      </div>
    </div>
  );
};
