/**
 * API client for FarBrain backend
 */

import axios from 'axios';
import type {
  Session,
  SessionCreateRequest,
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
};

export default api;
