import { create } from 'zustand'
import type { Agent } from '@/components/layout/RightPanel'

interface SessionState {
  selectedSessionId: string | null
  selectedAgent: Agent | null
  setSelectedSessionId: (id: string | null) => void
  setSelectedAgent: (agent: Agent | null) => void
  clearSelectedAgent: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  selectedSessionId: null,
  selectedAgent: null,
  setSelectedSessionId: (id) => set({ selectedSessionId: id }),
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
  clearSelectedAgent: () => set({ selectedAgent: null }),
}))
