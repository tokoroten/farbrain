/**
 * Session state management with localStorage persistence for passwords
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SessionPassword {
  sessionId: string;
  password: string;
}

interface SessionState {
  currentSessionId: string | null;
  sessionPasswords: SessionPassword[];
  setCurrentSession: (sessionId: string) => void;
  clearCurrentSession: () => void;
  savePassword: (sessionId: string, password: string) => void;
  getPassword: (sessionId: string) => string | undefined;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      currentSessionId: null,
      sessionPasswords: [],
      setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),
      clearCurrentSession: () => set({ currentSessionId: null }),
      savePassword: (sessionId, password) =>
        set((state) => ({
          sessionPasswords: [
            ...state.sessionPasswords.filter((sp) => sp.sessionId !== sessionId),
            { sessionId, password },
          ],
        })),
      getPassword: (sessionId) => {
        const passwords = get().sessionPasswords;
        return passwords.find((sp) => sp.sessionId === sessionId)?.password;
      },
    }),
    {
      name: 'farbrain-session',
    }
  )
);
