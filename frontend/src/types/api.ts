/**
 * API type definitions matching backend schemas
 */

export interface User {
  id: string;
  user_id: string;
  session_id: string;
  name: string;
  total_score: number;
  idea_count: number;
  rank: number | null;
  joined_at: string;
}

export interface UserRegisterRequest {
  name: string;
}

export interface UserRegisterResponse {
  user_id: string;
  name: string;
  created_at: string;
}

export interface SessionJoinRequest {
  user_id: string;
  name: string;
  password?: string;
}

export interface Session {
  id: string;
  title: string;
  description: string | null;
  start_time: string;
  duration: number;
  status: string;
  has_password: boolean;
  accepting_ideas: boolean;
  participant_count: number;
  idea_count: number;
  created_at: string;
  ended_at: string | null;
}

export interface SessionCreateRequest {
  title: string;
  description?: string;
  duration?: number;
  password?: string;
  formatting_prompt?: string;
  summarization_prompt?: string;
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface Idea {
  id: string;
  session_id: string;
  user_id: string;
  user_name: string;
  raw_text: string;
  formatted_text: string;
  x: number;
  y: number;
  cluster_id: number | null;
  novelty_score: number;
  timestamp: string;
}

export interface IdeaCreateRequest {
  session_id: string;
  user_id: string;
  raw_text: string;
}

export interface IdeaListResponse {
  ideas: Idea[];
  total: number;
}

export interface Point2D {
  x: number;
  y: number;
}

export interface ClusterData {
  id: number;
  label: string;
  convex_hull: Point2D[];
  idea_count: number;
  avg_novelty_score: number;
}

export interface IdeaVisualization {
  id: string;
  x: number;
  y: number;
  cluster_id: number | null;
  novelty_score: number;
  user_id: string;
  user_name: string;
  formatted_text: string;
  raw_text: string;
}

export interface VisualizationResponse {
  ideas: IdeaVisualization[];
  clusters: ClusterData[];
}

export interface ScoreboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
  total_score: number;
  idea_count: number;
  avg_novelty_score: number;
  top_idea: {
    id: string;
    formatted_text: string;
    novelty_score: number;
  } | null;
}

export interface ScoreboardResponse {
  rankings: ScoreboardEntry[];
}

// WebSocket event types
export type WebSocketEvent =
  | { type: 'idea_created'; data: IdeaVisualization }
  | { type: 'coordinates_updated'; data: { updates: Array<{ idea_id: string; x: number; y: number; cluster_id: number | null }> } }
  | { type: 'clusters_updated'; data: { clusters: ClusterData[] } }
  | { type: 'user_joined'; data: { user_id: string; user_name: string } }
  | { type: 'scoreboard_updated'; data: { rankings: ScoreboardEntry[] } }
  | { type: 'session_status_changed'; data: { status: string; accepting_ideas: boolean } }
  | { type: 'pong' };
