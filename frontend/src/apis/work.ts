import aiAxiosInstance from './aiAxiosInstance'
import type {
  CreateWorkRequest,
  WorkComment,
  WorkContextPreview,
  WorkCreateResponse,
  WorkItem,
  WorkLabel,
  WorkListResponse,
  WorkRelation,
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

export async function deleteWork(workId: string): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.delete<WorkItem>(`/work/${encodeURIComponent(workId)}`)
  return data
}

export async function createWorkComment(
  workId: string,
  body: string,
  resume = false,
): Promise<WorkComment> {
  const { data } = await aiAxiosInstance.post<WorkComment>(
    `/work/${encodeURIComponent(workId)}/comments`,
    {
      body,
      resume,
    },
  )
  return data
}

export async function createWorkRun(workId: string, message: string): Promise<WorkCreateResponse> {
  const { data } = await aiAxiosInstance.post<WorkCreateResponse>(
    `/work/${encodeURIComponent(workId)}/runs`,
    { message },
  )
  return data
}

export async function cancelWorkRun(runId: string): Promise<WorkRun> {
  const { data } = await aiAxiosInstance.post<WorkRun>(
    `/work-runs/${encodeURIComponent(runId)}/cancel`,
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

export async function listWorkLabels(
  sessionId: string,
): Promise<{ items: WorkLabel[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkLabel[]; totalCount: number }>(
    `/sessions/${encodeURIComponent(sessionId)}/work-labels`,
  )
  return data
}

export async function createWorkLabel(
  sessionId: string,
  payload: { name: string; color: string },
): Promise<WorkLabel> {
  const { data } = await aiAxiosInstance.post<WorkLabel>(
    `/sessions/${encodeURIComponent(sessionId)}/work-labels`,
    payload,
  )
  return data
}

export async function setWorkLabels(workId: string, labelIds: string[]): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/set-labels`,
    { labelIds },
  )
  return data
}

export async function listWorkRelations(
  workId: string,
): Promise<{ items: WorkRelation[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkRelation[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/relations`,
  )
  return data
}

export async function addWorkRelation(
  workId: string,
  targetWorkId: string,
  relationType: WorkRelation['relationType'],
): Promise<WorkRelation> {
  const { data } = await aiAxiosInstance.post<WorkRelation>(
    `/work/${encodeURIComponent(workId)}/relations`,
    { targetWorkId, relationType },
  )
  return data
}
