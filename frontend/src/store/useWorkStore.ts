import { create } from 'zustand'
import {
  createSessionWork,
  createWorkComment,
  listSessionWork,
  listWorkComments,
  moveWorkStatus,
  updateWorkFields,
} from '@/apis/work'
import { getFramePayload, isJsonObject, type AiRealtimeRawFrame } from '@/realtime/aiRealtimeTypes'
import { toWorkCreatedEvent } from '@/realtime/workEvents'
import type {
  CreateWorkRequest,
  WorkComment,
  WorkCreateResponse,
  WorkItem,
  WorkStatus,
} from '@/types/work'

type WorkState = {
  itemsBySessionId: Record<string, WorkItem[]>
  commentsByWorkId: Record<string, WorkComment[]>
  loadingBySessionId: Record<string, boolean>
  creatingBySessionId: Record<string, boolean>
  lastCreatedBySessionId: Record<string, WorkCreateResponse | undefined>
  lastError: string | null
  fetchSessionWork: (sessionId: string) => Promise<WorkItem[]>
  fetchComments: (workId: string) => Promise<WorkComment[]>
  createWork: (sessionId: string, payload: CreateWorkRequest) => Promise<WorkCreateResponse>
  moveStatus: (workId: string, status: WorkStatus) => Promise<WorkItem>
  updateFields: (
    workId: string,
    fields: { title?: string; description?: string },
  ) => Promise<WorkItem>
  addComment: (workId: string, body: string) => Promise<WorkComment>
  handleRealtimeFrame: (frame: AiRealtimeRawFrame) => void
  clearWorkState: () => void
}

export const useWorkStore = create<WorkState>((set) => ({
  itemsBySessionId: {},
  commentsByWorkId: {},
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
  fetchComments: async (workId) => {
    try {
      const response = await listWorkComments(workId)
      set((state) => ({
        commentsByWorkId: { ...state.commentsByWorkId, [workId]: response.items },
        lastError: null,
      }))
      return response.items
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : '작업 댓글 조회에 실패했습니다.' })
      throw error
    }
  },
  moveStatus: async (workId, status) => {
    try {
      const item = await moveWorkStatus(workId, status)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [item.sessionId]: upsertWorkItem(state.itemsBySessionId[item.sessionId] ?? [], item),
        },
        lastError: null,
      }))
      return item
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : '작업 상태 변경에 실패했습니다.' })
      throw error
    }
  },
  updateFields: async (workId, fields) => {
    try {
      const item = await updateWorkFields(workId, fields)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [item.sessionId]: upsertWorkItem(state.itemsBySessionId[item.sessionId] ?? [], item),
        },
        lastError: null,
      }))
      return item
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : '작업 내용 변경에 실패했습니다.' })
      throw error
    }
  },
  addComment: async (workId, body) => {
    try {
      const comment = await createWorkComment(workId, body)
      set((state) => ({
        commentsByWorkId: {
          ...state.commentsByWorkId,
          [workId]: [...(state.commentsByWorkId[workId] ?? []), comment],
        },
        lastError: null,
      }))
      return comment
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : '작업 댓글 추가에 실패했습니다.' })
      throw error
    }
  },
  handleRealtimeFrame: (frame) => {
    if (
      frame.type !== 'work.created' &&
      frame.type !== 'work.updated' &&
      frame.type !== 'work_comment.created'
    ) {
      return
    }
    const payload = getFramePayload(frame)
    if (!isJsonObject(payload) || !isWorkItem(payload.work)) {
      return
    }
    const work = payload.work
    const comment = isWorkComment(payload.comment) ? payload.comment : undefined
    set((state) => ({
      itemsBySessionId: {
        ...state.itemsBySessionId,
        [work.sessionId]: upsertWorkItem(state.itemsBySessionId[work.sessionId] ?? [], work),
      },
      commentsByWorkId:
        comment === undefined
          ? state.commentsByWorkId
          : {
              ...state.commentsByWorkId,
              [work.workId]: upsertWorkComment(state.commentsByWorkId[work.workId] ?? [], comment),
            },
      lastError: null,
    }))
  },
  clearWorkState: () =>
    set({
      itemsBySessionId: {},
      commentsByWorkId: {},
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

function upsertWorkComment(items: WorkComment[], item: WorkComment) {
  const index = items.findIndex((current) => current.commentId === item.commentId)
  if (index === -1) {
    return [...items, item]
  }
  return items.map((current, itemIndex) => (itemIndex === index ? item : current))
}

function isWorkItem(value: unknown): value is WorkItem {
  return (
    isJsonObject(value) && typeof value.workId === 'string' && typeof value.sessionId === 'string'
  )
}

function isWorkComment(value: unknown): value is WorkComment {
  return (
    isJsonObject(value) && typeof value.commentId === 'string' && typeof value.workId === 'string'
  )
}
