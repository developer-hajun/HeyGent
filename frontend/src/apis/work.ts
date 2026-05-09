import aiAxiosInstance from './aiAxiosInstance'
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

export async function listSessionWork(sessionId: string): Promise<WorkListResponse> {
  const { data } = await aiAxiosInstance.get<WorkListResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/work`,
  )
  return data
}

export async function createSessionWork(
  sessionId: string,
  payload: CreateWorkRequest,
): Promise<WorkCreateResponse> {
  const { data } = await aiAxiosInstance.post<WorkCreateResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/work`,
    payload,
  )
  return data
}

export async function getWork(workId: string): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.get<WorkItem>(`/work/${encodeURIComponent(workId)}`)
  return data
}

export async function moveWorkStatus(workId: string, status: WorkStatus): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/move-status`,
    {
      status,
    },
  )
  return data
}

export async function updateWorkFields(
  workId: string,
  fields: { title?: string; description?: string },
): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/update-fields`,
    fields,
  )
  return data
}

export async function updateWorkAssignee(
  workId: string,
  assigneeAgentId: string | null,
): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/assign`,
    {
      assigneeAgentId,
    },
  )
  return data
}

export async function createWorkComment(workId: string, body: string): Promise<WorkComment> {
  const { data } = await aiAxiosInstance.post<WorkComment>(
    `/work/${encodeURIComponent(workId)}/comments`,
    {
      body,
    },
  )
  return data
}

export async function listWorkComments(
  workId: string,
): Promise<{ items: WorkComment[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkComment[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/comments`,
  )
  return data
}

export async function listWorkRuns(
  workId: string,
): Promise<{ items: WorkRun[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkRun[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/runs`,
  )
  return data
}

export async function getWorkContextPreview(workId: string): Promise<WorkContextPreview> {
  const { data } = await aiAxiosInstance.get<WorkContextPreview>(
    `/work/${encodeURIComponent(workId)}/context-preview`,
  )
  return data
}
