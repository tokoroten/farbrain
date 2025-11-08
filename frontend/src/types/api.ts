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
  status: string;
  has_password: boolean;
  accepting_ideas: boolean;
  participant_count: number;
  idea_count: number;
  formatting_prompt: string | null;
  summarization_prompt: string | null;
  enable_dialogue_mode: boolean;
  enable_variation_mode: boolean;
  penalize_self_similarity: boolean;
  created_at: string;
}

export interface SessionCreateRequest {
  title: string;
  description?: string;
  password?: string;
  formatting_prompt?: string;
  summarization_prompt?: string;
  enable_dialogue_mode?: boolean;
  enable_variation_mode?: boolean;
  penalize_self_similarity?: boolean;
}

export interface SessionUpdateRequest {
  title?: string;
  description?: string;
  password?: string;
  accepting_ideas?: boolean;
  formatting_prompt?: string;
  summarization_prompt?: string;
  enable_dialogue_mode?: boolean;
  enable_variation_mode?: boolean;
  penalize_self_similarity?: boolean;
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
  closest_idea_id: string | null;
  timestamp: string;
}

export interface IdeaCreateRequest {
  session_id: string;
  user_id: string;
  raw_text: string;
  skip_formatting?: boolean;
  formatted_text?: string;  // Pre-formatted text (e.g., from variation generation)
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
  closest_idea_id: string | null;
  timestamp: string;
  coordinates_recalculated?: boolean;
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

// Dialogue types
export interface VariationRequest {
  session_id: string;
  keyword: string;
  count?: number;
}

export interface VariationResponse {
  variations: string[];
}

export interface DialogueRequest {
  session_id: string;
  message: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface DialogueResponse {
  type: 'question' | 'proposal';
  content: string;
  verbalized_idea?: string;  // Only present when type is 'proposal'
}

// WebSocket event types
export type WebSocketEvent =
  | { type: 'idea_created'; data: IdeaVisualization }
  | { type: 'coordinates_updated'; data: { updates: Array<{ idea_id: string; x: number; y: number; cluster_id: number | null }> } }
  | { type: 'clusters_updated'; data: { clusters: ClusterData[] } }
  | { type: 'clusters_recalculated'; data: {} }
  | { type: 'user_joined'; data: { user_id: string; user_name: string } }
  | { type: 'scoreboard_updated'; data: { rankings: ScoreboardEntry[] } }
  | { type: 'session_status_changed'; data: { status: string; accepting_ideas: boolean } }
  | { type: 'pong' };
