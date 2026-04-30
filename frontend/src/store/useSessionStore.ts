import { create } from 'zustand'
import type { Agent } from '@/components/layout/RightPanel'

export interface AgentPanelItem {
  id: string
  agent: Agent
  panelOpen: boolean
}

interface SessionState {
  selectedSessionId: string | null
  agentPanels: AgentPanelItem[]
  setSelectedSessionId: (id: string | null) => void
  addAgentPanel: (agent: Agent) => void
  removeAgentPanel: (id: string) => void
  toggleAgentPanel: (id: string) => void
}

export const useSessionStore = create<SessionState>((set, get) => ({
  selectedSessionId: null,
  agentPanels: [],
  setSelectedSessionId: (id) => set({ selectedSessionId: id }),
  addAgentPanel: (agent) => {
    const existing = get().agentPanels.find((p) => p.agent.name === agent.name)
    if (existing) return
    const id = `${agent.name}-${Date.now()}`
    set((s) => ({
      agentPanels: [...s.agentPanels, { id, agent, panelOpen: false }],
    }))
  },
  removeAgentPanel: (id) => set((s) => ({ agentPanels: s.agentPanels.filter((p) => p.id !== id) })),
  toggleAgentPanel: (id) =>
    set((s) => ({
      agentPanels: s.agentPanels.map((p) => (p.id === id ? { ...p, panelOpen: !p.panelOpen } : p)),
    })),
}))
