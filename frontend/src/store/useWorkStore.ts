import { create } from 'zustand'
import { createSessionWork, listSessionWork } from '@/apis/work'
import { toWorkCreatedEvent } from '@/realtime/workEvents'
import type { CreateWorkRequest, WorkCreateResponse, WorkItem } from '@/types/work'

type WorkState = {
  itemsBySessionId: Record<string, WorkItem[]>
  loadingBySessionId: Record<string, boolean>
  creatingBySessionId: Record<string, boolean>
  lastCreatedBySessionId: Record<string, WorkCreateResponse | undefined>
  lastError: string | null
  fetchSessionWork: (sessionId: string) => Promise<WorkItem[]>
  createWork: (sessionId: string, payload: CreateWorkRequest) => Promise<WorkCreateResponse>
  clearWorkState: () => void
}

export const useWorkStore = create<WorkState>((set) => ({
  itemsBySessionId: {},
  loadingBySessionId: {},
  creatingBySessionId: {},
  lastCreatedBySessionId: {},
  lastError: null,
  fetchSessionWork: async (sessionId) => {
    set((state) => ({
      loadingBySessionId: { ...state.loadingBySessionId, [sessionId]: true },
      lastError: null,
    }))

    try {
      const response = await listSessionWork(sessionId)
      set((state) => ({
        itemsBySessionId: { ...state.itemsBySessionId, [sessionId]: response.items },
        loadingBySessionId: { ...state.loadingBySessionId, [sessionId]: false },
        lastError: null,
      }))
      return response.items
    } catch (error) {
      set((state) => ({
        loadingBySessionId: { ...state.loadingBySessionId, [sessionId]: false },
        lastError: error instanceof Error ? error.message : '작업 목록을 불러오지 못했습니다.',
      }))
      throw error
    }
  },
  createWork: async (sessionId, payload) => {
    set((state) => ({
      creatingBySessionId: { ...state.creatingBySessionId, [sessionId]: true },
      lastError: null,
    }))

    try {
      const response = await createSessionWork(sessionId, payload)
      const event = toWorkCreatedEvent(response)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [sessionId]: upsertWorkItem(state.itemsBySessionId[sessionId] ?? [], event.work),
        },
        creatingBySessionId: { ...state.creatingBySessionId, [sessionId]: false },
        lastCreatedBySessionId: {
          ...state.lastCreatedBySessionId,
          [sessionId]: response,
        },
        lastError: null,
      }))
      return response
    } catch (error) {
      set((state) => ({
        creatingBySessionId: { ...state.creatingBySessionId, [sessionId]: false },
        lastError: error instanceof Error ? error.message : '작업 생성에 실패했습니다.',
      }))
      throw error
    }
  },
  clearWorkState: () =>
    set({
      itemsBySessionId: {},
      loadingBySessionId: {},
      creatingBySessionId: {},
      lastCreatedBySessionId: {},
      lastError: null,
    }),
}))

function upsertWorkItem(items: WorkItem[], item: WorkItem) {
  const index = items.findIndex((current) => current.workId === item.workId)
  if (index === -1) {
    return [item, ...items]
  }
  return items.map((current, itemIndex) => (itemIndex === index ? item : current))
}
