import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import { Bot } from 'lucide-react'
import type { Session } from '@/data/sessions'
import type { Agent } from '@/types/agent'
import { sessions as staticSessions } from '@/data/sessions'

export interface AgentPanelItem {
  id: string
  agent: Agent
  panelOpen: boolean
}

interface SessionState {
  selectedSessionId: string | null
  agentPanels: AgentPanelItem[]
  agentPanelsBySessionId: Record<string, AgentPanelItem[]>
  dynamicSessions: Session[]
  pinnedSessionIds: Set<string>
  setSelectedSessionId: (id: string | null) => void
  addAgentPanel: (agent: Agent) => void
  addAgentPanelToSession: (sessionId: string, agent: Agent) => void
  updateAgentPanel: (id: string, agent: Agent) => void
  updateAgentPanelInSession: (sessionId: string, id: string, agent: Agent) => void
  removeAgentPanel: (id: string) => void
  removeAgentPanelFromSession: (sessionId: string, id: string) => void
  toggleAgentPanel: (id: string) => void
  toggleAgentPanelInSession: (sessionId: string, id: string) => void
  getAgentPanelsForSession: (sessionId: string | null) => AgentPanelItem[]
  addDynamicSession: (session: Session) => void
  removeDynamicSession: (id: string) => void
  togglePinSession: (id: string) => void
  allSessions: () => Session[]
}

type PersistedSessionState = Partial<{
  selectedSessionId: string | null
  pinnedSessionIds: string[]
  agentPanelsBySessionId: Record<string, PersistedAgentPanelItem[]>
}>

type PersistedAgentPanelItem = {
  id: string
  agent: Pick<
    Agent,
    | 'name'
    | 'description'
    | 'instructions'
    | 'instructionsEntryFile'
    | 'instructionsFiles'
    | 'instructionsMode'
    | 'instructionsRootPath'
    | 'accent'
    | 'title'
    | 'role'
    | 'adapterType'
    | 'command'
    | 'model'
    | 'extraArgs'
    | 'webSearchEnabled'
    | 'bypassSandbox'
    | 'heartbeatEnabled'
    | 'intervalSec'
    | 'profileImage'
    | 'spriteId'
    | 'reportsToAgentId'
    | 'skills'
  >
  panelOpen: boolean
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      selectedSessionId: null,
      agentPanels: [],
      agentPanelsBySessionId: {},
      dynamicSessions: [],
      pinnedSessionIds: new Set(),

      setSelectedSessionId: (id) => set({ selectedSessionId: id }),

      addAgentPanel: (agent) => {
        const existing = get().agentPanels.find((p) => p.agent.name === agent.name)
        if (existing) return
        const id = `${agent.name}-${Date.now()}`
        set((s) => ({
          agentPanels: [...s.agentPanels, { id, agent, panelOpen: false }],
        }))
      },

      addAgentPanelToSession: (sessionId, agent) =>
        set((s) => {
          const current = s.agentPanelsBySessionId[sessionId] ?? []
          const existing = current.find((p) => p.agent.name === agent.name)
          if (existing) return s
          const id = `${agent.name}-${Date.now()}`
          return {
            agentPanelsBySessionId: {
              ...s.agentPanelsBySessionId,
              [sessionId]: [...current, { id, agent, panelOpen: false }],
            },
          }
        }),

      updateAgentPanel: (id, agent) =>
        set((s) => ({
          agentPanels: s.agentPanels.map((p) => (p.id === id ? { ...p, agent } : p)),
        })),

      updateAgentPanelInSession: (sessionId, id, agent) =>
        set((s) => {
          const current = s.agentPanelsBySessionId[sessionId] ?? []
          return {
            agentPanelsBySessionId: {
              ...s.agentPanelsBySessionId,
              [sessionId]: current.map((p) => (p.id === id ? { ...p, agent } : p)),
            },
          }
        }),

      removeAgentPanel: (id) =>
        set((s) => ({ agentPanels: s.agentPanels.filter((p) => p.id !== id) })),

      removeAgentPanelFromSession: (sessionId, id) =>
        set((s) => {
          const current = s.agentPanelsBySessionId[sessionId] ?? []
          return {
            agentPanelsBySessionId: {
              ...s.agentPanelsBySessionId,
              [sessionId]: current.filter((p) => p.id !== id),
            },
          }
        }),

      toggleAgentPanel: (id) =>
        set((s) => ({
          agentPanels: s.agentPanels.map((p) =>
            p.id === id ? { ...p, panelOpen: !p.panelOpen } : p,
          ),
        })),

      toggleAgentPanelInSession: (sessionId, id) =>
        set((s) => {
          const current = s.agentPanelsBySessionId[sessionId] ?? []
          return {
            agentPanelsBySessionId: {
              ...s.agentPanelsBySessionId,
              [sessionId]: current.map((p) =>
                p.id === id ? { ...p, panelOpen: !p.panelOpen } : p,
              ),
            },
          }
        }),

      getAgentPanelsForSession: (sessionId) => {
        if (sessionId === null) return []
        return get().agentPanelsBySessionId[sessionId] ?? []
      },

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

      allSessions: () => {
        const { dynamicSessions } = get()
        return [...dynamicSessions, ...staticSessions]
      },
    }),
    {
      name: 'heygent-session-ui',
      storage: createJSONStorage(() => localStorage),
      // Set은 JSON으로 직접 저장되지 않으므로 로컬 UI 상태만 배열로 직렬화한다.
      partialize: (state) => ({
        selectedSessionId: state.selectedSessionId,
        pinnedSessionIds: [...state.pinnedSessionIds],
        agentPanelsBySessionId: serializeAgentPanelsBySessionId(state.agentPanelsBySessionId),
      }),
      merge: (persisted, current) => {
        const value = persisted as PersistedSessionState
        return {
          ...current,
          selectedSessionId: value.selectedSessionId ?? current.selectedSessionId,
          pinnedSessionIds: new Set(value.pinnedSessionIds ?? []),
          agentPanelsBySessionId: deserializeAgentPanelsBySessionId(
            value.agentPanelsBySessionId ?? {},
          ),
        }
      },
    },
  ),
)

function serializeAgentPanelsBySessionId(
  source: Record<string, AgentPanelItem[]>,
): Record<string, PersistedAgentPanelItem[]> {
  return Object.fromEntries(
    Object.entries(source).map(([sessionId, panels]) => [
      sessionId,
      panels.map((panel) => ({
        id: panel.id,
        agent: {
          name: panel.agent.name,
          description: panel.agent.description,
          instructions: panel.agent.instructions,
          instructionsEntryFile: panel.agent.instructionsEntryFile,
          instructionsFiles: panel.agent.instructionsFiles,
          instructionsMode: panel.agent.instructionsMode,
          instructionsRootPath: panel.agent.instructionsRootPath,
          accent: panel.agent.accent,
          title: panel.agent.title,
          role: panel.agent.role,
          adapterType: panel.agent.adapterType,
          command: panel.agent.command,
          model: panel.agent.model,
          extraArgs: panel.agent.extraArgs,
          webSearchEnabled: panel.agent.webSearchEnabled,
          bypassSandbox: panel.agent.bypassSandbox,
          heartbeatEnabled: panel.agent.heartbeatEnabled,
          intervalSec: panel.agent.intervalSec,
          profileImage: panel.agent.profileImage,
          spriteId: panel.agent.spriteId,
          reportsToAgentId: panel.agent.reportsToAgentId,
          skills: panel.agent.skills,
        },
        panelOpen: panel.panelOpen,
      })),
    ]),
  )
}

function deserializeAgentPanelsBySessionId(
  source: Record<string, PersistedAgentPanelItem[]>,
): Record<string, AgentPanelItem[]> {
  return Object.fromEntries(
    Object.entries(source).map(([sessionId, panels]) => [
      sessionId,
      panels.map((panel) => ({
        id: panel.id,
        agent: {
          ...panel.agent,
          icon: Bot,
        },
        panelOpen: panel.panelOpen,
      })),
    ]),
  )
}
