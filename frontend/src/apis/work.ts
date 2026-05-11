import aiAxiosInstance from './aiAxiosInstance'
import type {
  CreateChildWorkRequest,
  CreateWorkRequest,
  WorkComment,
  WorkContextPreview,
  WorkCreateResponse,
  WorkDocument,
  WorkDocumentRevision,
  WorkFlowResponse,
  WorkInteraction,
  WorkItem,
  WorkLabel,
  WorkListResponse,
  WorkProduct,
  WorkRecoveryAction,
  WorkRelation,
  WorkRun,
  WorkStatus,
  WorkWake,
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

export async function getWorkFlow(workId: string): Promise<WorkFlowResponse> {
  const { data } = await aiAxiosInstance.get<WorkFlowResponse>(
    `/work/${encodeURIComponent(workId)}/flow`,
  )
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

export async function updateWorkParent(workId: string, parentId: string | null): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/update-parent`,
    { parentId },
  )
  return data
}

export async function updateSessionWorkFlowOrder(
  sessionId: string,
  workIds: string[],
): Promise<WorkListResponse> {
  const { data } = await aiAxiosInstance.post<WorkListResponse>(
    `/sessions/${encodeURIComponent(sessionId)}/work/flow-order`,
    { workIds },
  )
  return data
}

export async function updateWorkFlowOrder(
  workId: string,
  workIds: string[],
): Promise<WorkListResponse> {
  const { data } = await aiAxiosInstance.post<WorkListResponse>(
    `/work/${encodeURIComponent(workId)}/flow-order`,
    { workIds },
  )
  return data
}

export async function createChildWork(
  workId: string,
  payload: CreateChildWorkRequest,
): Promise<WorkItem> {
  const { data } = await aiAxiosInstance.post<WorkItem>(
    `/work/${encodeURIComponent(workId)}/children`,
    payload,
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

export async function listWorkWakes(
  workId: string,
): Promise<{ items: WorkWake[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkWake[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/wakes`,
  )
  return data
}

export async function listWorkRecoveryActions(
  workId: string,
): Promise<{ items: WorkRecoveryAction[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{
    items: WorkRecoveryAction[]
    totalCount: number
  }>(`/work/${encodeURIComponent(workId)}/recovery-actions`)
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

export async function removeWorkRelation(
  workId: string,
  targetWorkId: string,
  relationType: WorkRelation['relationType'],
): Promise<{ deleted: boolean }> {
  const { data } = await aiAxiosInstance.delete<{ deleted: boolean }>(
    `/work/${encodeURIComponent(workId)}/relations/${encodeURIComponent(relationType)}/${encodeURIComponent(targetWorkId)}`,
  )
  return data
}

export async function listWorkDocuments(
  workId: string,
): Promise<{ items: WorkDocument[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkDocument[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/documents`,
  )
  return data
}

export async function upsertWorkDocument(
  workId: string,
  documentKey: string,
  payload: { title: string; body: string; format?: string },
): Promise<WorkDocument> {
  const { data } = await aiAxiosInstance.put<WorkDocument>(
    `/work/${encodeURIComponent(workId)}/documents/${encodeURIComponent(documentKey)}`,
    payload,
  )
  return data
}

export async function deleteWorkDocument(
  workId: string,
  documentKey: string,
): Promise<{ deleted: boolean }> {
  const { data } = await aiAxiosInstance.delete<{ deleted: boolean }>(
    `/work/${encodeURIComponent(workId)}/documents/${encodeURIComponent(documentKey)}`,
  )
  return data
}

export async function listWorkDocumentRevisions(
  workId: string,
  documentKey: string,
): Promise<{ items: WorkDocumentRevision[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{
    items: WorkDocumentRevision[]
    totalCount: number
  }>(`/work/${encodeURIComponent(workId)}/documents/${encodeURIComponent(documentKey)}/revisions`)
  return data
}

export async function listWorkProducts(
  workId: string,
): Promise<{ items: WorkProduct[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkProduct[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/work-products`,
  )
  return data
}

export async function createWorkProduct(
  workId: string,
  payload: {
    title: string
    summary?: string | null
    productType?: string
    status?: string
    reviewState?: string
    uri?: string | null
    metadata?: Record<string, unknown>
  },
): Promise<WorkProduct> {
  const { data } = await aiAxiosInstance.post<WorkProduct>(
    `/work/${encodeURIComponent(workId)}/work-products`,
    payload,
  )
  return data
}

export async function updateWorkProduct(
  productId: string,
  payload: {
    title?: string
    summary?: string | null
    status?: string
    reviewState?: string
    uri?: string | null
    metadata?: Record<string, unknown>
  },
): Promise<WorkProduct> {
  const { data } = await aiAxiosInstance.post<WorkProduct>(
    `/work-products/${encodeURIComponent(productId)}/update-fields`,
    payload,
  )
  return data
}

export async function deleteWorkProduct(productId: string): Promise<{ deleted: boolean }> {
  const { data } = await aiAxiosInstance.delete<{ deleted: boolean }>(
    `/work-products/${encodeURIComponent(productId)}`,
  )
  return data
}

export async function listWorkInteractions(
  workId: string,
): Promise<{ items: WorkInteraction[]; totalCount: number }> {
  const { data } = await aiAxiosInstance.get<{ items: WorkInteraction[]; totalCount: number }>(
    `/work/${encodeURIComponent(workId)}/interactions`,
  )
  return data
}

export async function createWorkInteraction(
  workId: string,
  payload: {
    kind: WorkInteraction['kind']
    title?: string | null
    body?: string | null
    payload?: Record<string, unknown>
    continuationPolicy?: WorkInteraction['continuationPolicy']
  },
): Promise<WorkInteraction> {
  const { data } = await aiAxiosInstance.post<WorkInteraction>(
    `/work/${encodeURIComponent(workId)}/interactions`,
    payload,
  )
  return data
}

export async function respondWorkInteraction(
  interactionId: string,
  action: 'accept' | 'reject' | 'cancel' | 'respond',
  response?: Record<string, unknown>,
): Promise<WorkInteraction> {
  const { data } = await aiAxiosInstance.post<WorkInteraction>(
    `/work-interactions/${encodeURIComponent(interactionId)}/${action}`,
    action === 'respond' ? { response: response ?? {} } : {},
  )
  return data
}
