import { create } from 'zustand'
import type { Agent } from '@/components/layout/RightPanel'
import type { Session } from '@/data/sessions'
import { sessions as staticSessions } from '@/data/sessions'

export interface AgentPanelItem {
  id: string
  agent: Agent
  panelOpen: boolean
}

interface SessionState {
  selectedSessionId: string | null
  agentPanels: AgentPanelItem[]
  dynamicSessions: Session[]
  pinnedSessionIds: Set<string>
  hiddenSessionIds: Set<string>
  setSelectedSessionId: (id: string | null) => void
  addAgentPanel: (agent: Agent) => void
  removeAgentPanel: (id: string) => void
  toggleAgentPanel: (id: string) => void
  addDynamicSession: (session: Session) => void
  removeDynamicSession: (id: string) => void
  togglePinSession: (id: string) => void
  hideSession: (id: string) => void
  allSessions: () => Session[]
}

export const useSessionStore = create<SessionState>((set, get) => ({
  selectedSessionId: null,
  agentPanels: [],
  dynamicSessions: [],
  pinnedSessionIds: new Set(),
  hiddenSessionIds: new Set(),

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

  addDynamicSession: (session) =>
    set((s) => ({
      dynamicSessions: [session, ...s.dynamicSessions],
    })),

  removeDynamicSession: (id) =>
    set((s) => {
      const pinned = new Set(s.pinnedSessionIds)
      pinned.delete(id)
      return {
        dynamicSessions: s.dynamicSessions.filter((d) => d.id !== id),
        pinnedSessionIds: pinned,
      }
    }),

  togglePinSession: (id) =>
    set((s) => {
      const next = new Set(s.pinnedSessionIds)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return { pinnedSessionIds: next }
    }),

  hideSession: (id) =>
    set((s) => {
      const hidden = new Set(s.hiddenSessionIds)
      hidden.add(id)
      const pinned = new Set(s.pinnedSessionIds)
      pinned.delete(id)
      return { hiddenSessionIds: hidden, pinnedSessionIds: pinned }
    }),

  allSessions: () => {
    const { dynamicSessions, hiddenSessionIds } = get()
    return [
      ...dynamicSessions.filter((s) => !hiddenSessionIds.has(s.id)),
      ...staticSessions.filter((s) => !hiddenSessionIds.has(s.id)),
    ]
  },
}))
