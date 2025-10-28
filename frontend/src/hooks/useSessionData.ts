/**
 * Custom hook for managing session data and WebSocket updates
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type {
  Session,
  IdeaVisualization,
  ClusterData,
  ScoreboardEntry,
  WebSocketEvent,
} from '../types/api';

interface UseSessionDataOptions {
  sessionId: string;
  onWebSocketMessage?: (event: WebSocketEvent) => void;
}

interface UseSessionDataReturn {
  session: Session | null;
  ideas: IdeaVisualization[];
  clusters: ClusterData[];
  scoreboard: ScoreboardEntry[];
  isLoading: boolean;
  error: string | null;
  setIdeas: React.Dispatch<React.SetStateAction<IdeaVisualization[]>>;
  setClusters: React.Dispatch<React.SetStateAction<ClusterData[]>>;
  setScoreboard: React.Dispatch<React.SetStateAction<ScoreboardEntry[]>>;
  setSession: React.Dispatch<React.SetStateAction<Session | null>>;
  fetchSessionData: () => Promise<void>;
  fetchVisualizationData: () => Promise<void>;
}

export const useSessionData = ({
  sessionId,
  onWebSocketMessage,
}: UseSessionDataOptions): UseSessionDataReturn => {
  const [session, setSession] = useState<Session | null>(null);
  const [ideas, setIdeas] = useState<IdeaVisualization[]>([]);
  const [clusters, setClusters] = useState<ClusterData[]>([]);
  const [scoreboard, setScoreboard] = useState<ScoreboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessionData = useCallback(async () => {
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
  }, [sessionId]);

  const fetchVisualizationData = useCallback(async () => {
    try {
      const vizData = await api.visualization.get(sessionId);
      setIdeas(vizData.ideas);
      setClusters(vizData.clusters);
      console.log('Visualization data refreshed (ideas and clusters only)');
    } catch (err) {
      console.error('Failed to refresh visualization data:', err);
    }
  }, [sessionId]);

  // Initial data fetch
  useEffect(() => {
    fetchSessionData();
  }, [fetchSessionData]);

  // Auto-refresh scoreboard every 10 seconds
  useEffect(() => {
    const scoreboardInterval = setInterval(async () => {
      try {
        const scoreboardData = await api.visualization.getScoreboard(sessionId);
        setScoreboard(scoreboardData.rankings);
      } catch (err) {
        console.error('Failed to refresh scoreboard:', err);
      }
    }, 10000);

    return () => clearInterval(scoreboardInterval);
  }, [sessionId]);

  return {
    session,
    ideas,
    clusters,
    scoreboard,
    isLoading,
    error,
    setIdeas,
    setClusters,
    setScoreboard,
    setSession,
    fetchSessionData,
    fetchVisualizationData,
  };
};
