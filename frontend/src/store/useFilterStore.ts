import { create } from 'zustand'

type AgentStatusFilter = 'all' | 'running' | 'idle' | 'completed'
type SessionSortOrder = 'latest' | 'oldest'

interface FilterState {
  // 에이전트 상태 페이지 필터
  agentStatusFilter: AgentStatusFilter
  setAgentStatusFilter: (filter: AgentStatusFilter) => void

  // 세션 목록 정렬
  sessionSortOrder: SessionSortOrder
  setSessionSortOrder: (order: SessionSortOrder) => void

  resetFilters: () => void
}

const initialState = {
  agentStatusFilter: 'all' as AgentStatusFilter,
  sessionSortOrder: 'latest' as SessionSortOrder,
}

export const useFilterStore = create<FilterState>((set) => ({
  ...initialState,
  setAgentStatusFilter: (filter) => set({ agentStatusFilter: filter }),
  setSessionSortOrder: (order) => set({ sessionSortOrder: order }),
  resetFilters: () => set(initialState),
}))
