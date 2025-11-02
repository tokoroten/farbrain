/**
 * API client for FarBrain backend
 */

import axios from 'axios';
import { downloadFile } from '../utils/download';
import type {
  Session,
  SessionCreateRequest,
  SessionUpdateRequest,
  SessionListResponse,
  SessionJoinRequest,
  User,
  UserRegisterRequest,
  UserRegisterResponse,
  Idea,
  IdeaCreateRequest,
  IdeaListResponse,
  VisualizationResponse,
  ScoreboardResponse,
  VariationRequest,
  VariationResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Health check
  health: async (): Promise<{ status: string }> => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // User endpoints
  users: {
    register: async (data: UserRegisterRequest): Promise<UserRegisterResponse> => {
      const response = await apiClient.post('/api/users/register', data);
      return response.data;
    },

    join: async (sessionId: string, data: SessionJoinRequest): Promise<User> => {
      const response = await apiClient.post(`/api/users/${sessionId}/join`, data);
      return response.data;
    },

    getUser: async (sessionId: string, userId: string): Promise<User> => {
      const response = await apiClient.get(`/api/users/${sessionId}/${userId}`);
      return response.data;
    },
  },

  // Session endpoints
  sessions: {
    create: async (data: SessionCreateRequest): Promise<Session> => {
      const response = await apiClient.post('/api/sessions/', data);
      return response.data;
    },

    list: async (activeOnly = false): Promise<SessionListResponse> => {
      const response = await apiClient.get('/api/sessions/', {
        params: { active_only: activeOnly },
      });
      return response.data;
    },

    get: async (sessionId: string): Promise<Session> => {
      const response = await apiClient.get(`/api/sessions/${sessionId}`);
      return response.data;
    },

    end: async (sessionId: string): Promise<Session> => {
      const response = await apiClient.post(`/api/sessions/${sessionId}/end`);
      return response.data;
    },

    toggleAccepting: async (sessionId: string, accepting: boolean): Promise<Session> => {
      const response = await apiClient.post(`/api/sessions/${sessionId}/toggle-accepting`, {
        accepting_ideas: accepting,
      });
      return response.data;
    },

    update: async (sessionId: string, data: SessionUpdateRequest): Promise<Session> => {
      const response = await apiClient.patch(`/api/sessions/${sessionId}`, data);
      return response.data;
    },

    delete: async (sessionId: string): Promise<{ message: string; session_id: string }> => {
      const response = await apiClient.delete(`/api/sessions/${sessionId}`);
      return response.data;
    },

    export: async (sessionId: string): Promise<void> => {
      const response = await apiClient.get(`/api/sessions/${sessionId}/export`, {
        responseType: 'blob',
      });

      await downloadFile(
        response,
        `ideas_${sessionId}_${new Date().toISOString().split('T')[0]}.csv`
      );
    },
  },

  // Idea endpoints
  ideas: {
    create: async (data: IdeaCreateRequest): Promise<Idea> => {
      const response = await apiClient.post('/api/ideas/', data);
      return response.data;
    },

    list: async (sessionId: string): Promise<IdeaListResponse> => {
      const response = await apiClient.get(`/api/ideas/${sessionId}`);
      return response.data;
    },

    get: async (sessionId: string, ideaId: string): Promise<Idea> => {
      const response = await apiClient.get(`/api/ideas/${sessionId}/${ideaId}`);
      return response.data;
    },

    delete: async (ideaId: string, userId: string, adminPassword?: string): Promise<{ message: string; idea_id: string }> => {
      const response = await apiClient.delete(`/api/ideas/${ideaId}`, {
        data: {
          user_id: userId,
          admin_password: adminPassword || null,
        },
      });
      return response.data;
    },

    vote: async (ideaId: string, userId: string): Promise<{ message: string; vote_id: string }> => {
      const response = await apiClient.post(`/api/ideas/${ideaId}/vote`, null, {
        params: { user_id: userId },
      });
      return response.data;
    },

    unvote: async (ideaId: string, userId: string): Promise<{ message: string }> => {
      const response = await apiClient.delete(`/api/ideas/${ideaId}/vote`, {
        params: { user_id: userId },
      });
      return response.data;
    },
  },

  // Visualization endpoints
  visualization: {
    get: async (sessionId: string, userId: string): Promise<VisualizationResponse> => {
      const response = await apiClient.get(`/api/visualization/${sessionId}`, {
        params: { user_id: userId },
      });
      return response.data;
    },

    getScoreboard: async (sessionId: string): Promise<ScoreboardResponse> => {
      const response = await apiClient.get(`/api/visualization/${sessionId}/scoreboard`);
      return response.data;
    },
  },

  // Auth endpoints
  auth: {
    verifyAdmin: async (password: string): Promise<{ success: boolean; message: string }> => {
      const response = await apiClient.post('/api/admin/verify', { password });
      return response.data;
    },
  },

  // Debug endpoints
  debug: {
    forceCluster: async (sessionId: string, useLlmLabels = false, fixedClusterCount: number | null = null): Promise<any> => {
      const response = await apiClient.post('/api/debug/force-cluster', {
        session_id: sessionId,
        use_llm_labels: useLlmLabels,
        fixed_cluster_count: fixedClusterCount,
      });
      return response.data;
    },

    createTestSession: async (): Promise<{
      message: string;
      session_id: string;
      session_title: string;
      user_count: number;
      idea_count: number;
      cluster_count: number;
    }> => {
      const response = await apiClient.post('/api/debug/create-test-session');
      return response.data;
    },
  },

  // Dialogue endpoints
  dialogue: {
    generateVariations: async (data: VariationRequest): Promise<VariationResponse> => {
      const response = await apiClient.post('/api/dialogue/variations', data);
      return response.data;
    },
  },

  // Report endpoints
  reports: {
    downloadMarkdown: async (sessionId: string): Promise<void> => {
      const response = await apiClient.get(`/api/reports/${sessionId}/markdown`, {
        responseType: 'blob',
      });

      await downloadFile(
        response,
        `report_${sessionId}_${new Date().toISOString().split('T')[0]}.md`
      );
    },

    downloadPDF: async (sessionId: string): Promise<void> => {
      const response = await apiClient.get(`/api/reports/${sessionId}/pdf`, {
        responseType: 'blob',
      });

      await downloadFile(
        response,
        `report_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`
      );
    },
  },
};

export default api;
