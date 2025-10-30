/**
 * API client for FarBrain backend
 */

import axios from 'axios';
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

      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `ideas_${sessionId}_${new Date().toISOString().split('T')[0]}.csv`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
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
  },

  // Visualization endpoints
  visualization: {
    get: async (sessionId: string): Promise<VisualizationResponse> => {
      const response = await apiClient.get(`/api/visualization/${sessionId}`);
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

  // Report endpoints
  reports: {
    downloadMarkdown: async (sessionId: string): Promise<void> => {
      const response = await apiClient.get(`/api/reports/${sessionId}/markdown`, {
        responseType: 'blob',
      });

      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${sessionId}_${new Date().toISOString().split('T')[0]}.md`;

      if (contentDisposition) {
        // Handle RFC 5987 encoding: filename*=UTF-8''encoded_name
        const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/);
        if (filenameStarMatch) {
          filename = decodeURIComponent(filenameStarMatch[1]);
        } else {
          // Fallback to standard filename
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },

    downloadPDF: async (sessionId: string): Promise<void> => {
      const response = await apiClient.get(`/api/reports/${sessionId}/pdf`, {
        responseType: 'blob',
      });

      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${sessionId}_${new Date().toISOString().split('T')[0]}.pdf`;

      if (contentDisposition) {
        // Handle RFC 5987 encoding: filename*=UTF-8''encoded_name
        const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/);
        if (filenameStarMatch) {
          filename = decodeURIComponent(filenameStarMatch[1]);
        } else {
          // Fallback to standard filename
          const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
          if (filenameMatch) {
            filename = filenameMatch[1];
          }
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
  },
};

export default api;
