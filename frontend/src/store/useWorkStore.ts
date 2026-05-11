import { create } from 'zustand'
import {
  createWorkLabel,
  createSessionWork,
  createWorkRun,
  createWorkComment,
  deleteWork,
  listWorkLabels,
  listSessionWork,
  listWorkComments,
  moveWorkStatus,
  setWorkLabels,
  updateWorkAssignee,
  updateWorkFields,
} from '@/apis/work'
import { getFramePayload, isJsonObject, type AiRealtimeRawFrame } from '@/realtime/aiRealtimeTypes'
import { toWorkCreatedEvent } from '@/realtime/workEvents'
import type {
  CreateWorkRequest,
  WorkComment,
  WorkCreateResponse,
  WorkItem,
  WorkLabel,
  WorkStatus,
} from '@/types/work'
import { getApiErrorMessage } from '@/utils/apiErrorMessage'

type WorkState = {
  itemsBySessionId: Record<string, WorkItem[]>
  commentsByWorkId: Record<string, WorkComment[]>
  labelsBySessionId: Record<string, WorkLabel[]>
  loadingBySessionId: Record<string, boolean>
  creatingBySessionId: Record<string, boolean>
  lastCreatedBySessionId: Record<string, WorkCreateResponse | undefined>
  lastError: string | null
  fetchSessionWork: (sessionId: string) => Promise<WorkItem[]>
  fetchComments: (workId: string) => Promise<WorkComment[]>
  fetchLabels: (sessionId: string) => Promise<WorkLabel[]>
  createWork: (sessionId: string, payload: CreateWorkRequest) => Promise<WorkCreateResponse>
  createRun: (workId: string, message: string) => Promise<WorkCreateResponse>
  moveStatus: (workId: string, status: WorkStatus) => Promise<WorkItem>
  updateFields: (
    workId: string,
    fields: { title?: string; description?: string },
  ) => Promise<WorkItem>
  updateAssignee: (workId: string, assigneeAgentId: string | null) => Promise<WorkItem>
  addComment: (workId: string, body: string, resume?: boolean) => Promise<WorkComment>
  createLabel: (sessionId: string, payload: { name: string; color: string }) => Promise<WorkLabel>
  setLabels: (workId: string, labelIds: string[]) => Promise<WorkItem>
  deleteWorkItem: (workId: string) => Promise<WorkItem>
  handleRealtimeFrame: (frame: AiRealtimeRawFrame) => void
  clearWorkState: () => void
}

export const useWorkStore = create<WorkState>((set) => ({
  itemsBySessionId: {},
  commentsByWorkId: {},
  labelsBySessionId: {},
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
        lastError: getApiErrorMessage(error, { fallback: '작업 목록을 불러오지 못했습니다.' }),
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
        lastError: getApiErrorMessage(error, { fallback: '작업 생성에 실패했습니다.' }),
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
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 댓글 조회에 실패했습니다.' }) })
      throw error
    }
  },
  fetchLabels: async (sessionId) => {
    try {
      const response = await listWorkLabels(sessionId)
      set((state) => ({
        labelsBySessionId: { ...state.labelsBySessionId, [sessionId]: response.items },
        lastError: null,
      }))
      return response.items
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 라벨 조회에 실패했습니다.' }) })
      throw error
    }
  },
  createRun: async (workId, message) => {
    try {
      const response = await createWorkRun(workId, message)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [response.work.sessionId]: upsertWorkItem(
            state.itemsBySessionId[response.work.sessionId] ?? [],
            response.work,
          ),
        },
        lastError: null,
      }))
      return response
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 실행에 실패했습니다.' }) })
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
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 상태 변경에 실패했습니다.' }) })
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
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 내용 변경에 실패했습니다.' }) })
      throw error
    }
  },
  updateAssignee: async (workId, assigneeAgentId) => {
    try {
      const item = await updateWorkAssignee(workId, assigneeAgentId)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [item.sessionId]: upsertWorkItem(state.itemsBySessionId[item.sessionId] ?? [], item),
        },
        lastError: null,
      }))
      return item
    } catch (error) {
      set({
        lastError: getApiErrorMessage(error, { fallback: '작업 담당자 변경에 실패했습니다.' }),
      })
      throw error
    }
  },
  addComment: async (workId, body, resume = false) => {
    try {
      const comment = await createWorkComment(workId, body, resume)
      set((state) => ({
        commentsByWorkId: {
          ...state.commentsByWorkId,
          [workId]: [...(state.commentsByWorkId[workId] ?? []), comment],
        },
        lastError: null,
      }))
      return comment
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 댓글 추가에 실패했습니다.' }) })
      throw error
    }
  },
  createLabel: async (sessionId, payload) => {
    try {
      const label = await createWorkLabel(sessionId, payload)
      set((state) => ({
        labelsBySessionId: {
          ...state.labelsBySessionId,
          [sessionId]: upsertWorkLabel(state.labelsBySessionId[sessionId] ?? [], label),
        },
        lastError: null,
      }))
      return label
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 라벨 생성에 실패했습니다.' }) })
      throw error
    }
  },
  setLabels: async (workId, labelIds) => {
    try {
      const item = await setWorkLabels(workId, labelIds)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [item.sessionId]: upsertWorkItem(state.itemsBySessionId[item.sessionId] ?? [], item),
        },
        lastError: null,
      }))
      return item
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 라벨 변경에 실패했습니다.' }) })
      throw error
    }
  },
  deleteWorkItem: async (workId) => {
    try {
      const item = await deleteWork(workId)
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [item.sessionId]: (state.itemsBySessionId[item.sessionId] ?? []).filter(
            (current) => current.workId !== workId,
          ),
        },
        lastError: null,
      }))
      return item
    } catch (error) {
      set({ lastError: getApiErrorMessage(error, { fallback: '작업 삭제에 실패했습니다.' }) })
      throw error
    }
  },
  handleRealtimeFrame: (frame) => {
    if (frame.type.startsWith('work_label.')) {
      const payload = getFramePayload(frame)
      if (!isJsonObject(payload)) return
      const label = isWorkLabel(payload.label) ? payload.label : undefined
      if (label !== undefined) {
        set((state) => ({
          labelsBySessionId: {
            ...state.labelsBySessionId,
            [label.sessionId]: upsertWorkLabel(
              state.labelsBySessionId[label.sessionId] ?? [],
              label,
            ),
          },
          lastError: null,
        }))
      }
      return
    }
    if (!frame.type.startsWith('work.') && !frame.type.startsWith('work_')) {
      return
    }
    const payload = getFramePayload(frame)
    if (!isJsonObject(payload) || !isWorkItem(payload.work)) {
      return
    }
    const work = payload.work
    if (frame.type === 'work.deleted') {
      set((state) => ({
        itemsBySessionId: {
          ...state.itemsBySessionId,
          [work.sessionId]: (state.itemsBySessionId[work.sessionId] ?? []).filter(
            (item) => item.workId !== work.workId,
          ),
        },
        lastError: null,
      }))
      return
    }
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
      labelsBySessionId: {},
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

function upsertWorkLabel(items: WorkLabel[], item: WorkLabel) {
  const index = items.findIndex((current) => current.labelId === item.labelId)
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

function isWorkLabel(value: unknown): value is WorkLabel {
  return (
    isJsonObject(value) && typeof value.labelId === 'string' && typeof value.sessionId === 'string'
  )
}
