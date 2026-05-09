import axios from 'axios'
import { useAuthStore } from '@/store/useAuthStore'
import type {
  CreateWorkRequest,
  WorkComment,
  WorkContextPreview,
  WorkCreateResponse,
  WorkItem,
  WorkListResponse,
  WorkRun,
  WorkStatus,
} from '@/types/work'

const workApi = axios.create({
  baseURL: import.meta.env.VITE_AI_API_BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

workApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function listSessionWork(sessionId: string): Promise<WorkListResponse> {
  const { data } = await workApi.get<WorkListResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/work`,
  )
  return data
}

export async function createSessionWork(
  sessionId: string,
  payload: CreateWorkRequest,
): Promise<WorkCreateResponse> {
  const { data } = await workApi.post<WorkCreateResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/work`,
    payload,
  )
  return data
}

export async function getWork(workId: string): Promise<WorkItem> {
  const { data } = await workApi.get<WorkItem>(`/work/${encodeURIComponent(workId)}`)
  return data
}

export async function moveWorkStatus(workId: string, status: WorkStatus): Promise<WorkItem> {
  const { data } = await workApi.post<WorkItem>(`/work/${encodeURIComponent(workId)}/move-status`, {
    status,
  })
  return data
}

export async function createWorkComment(workId: string, body: string): Promise<WorkComment> {
  const { data } = await workApi.post<WorkComment>(`/work/${encodeURIComponent(workId)}/comments`, {
    body,
  })
  return data
}

export async function listWorkComments(
  workId: string,
): Promise<{ items: WorkComment[]; totalCount: number }> {
  const { data } = await workApi.get<{ items: WorkComment[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/comments`,
  )
  return data
}

export async function listWorkRuns(
  workId: string,
): Promise<{ items: WorkRun[]; totalCount: number }> {
  const { data } = await workApi.get<{ items: WorkRun[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/runs`,
  )
  return data
}

export async function getWorkContextPreview(workId: string): Promise<WorkContextPreview> {
  const { data } = await workApi.get<WorkContextPreview>(
    `/work/${encodeURIComponent(workId)}/context-preview`,
  )
  return data
}
