import aiAxiosInstance from './aiAxiosInstance'

export type WorkflowTemplateNode = {
  slotKey: string
  title: string
  description: string
  assigneeAgentId: string | null
  templateKey: string | null
  positionX: number
  positionY: number
}

export type WorkflowTemplateEdge = {
  sourceSlotKey: string
  targetSlotKey: string
}

export type WorkflowTemplateGraph = {
  nodes: WorkflowTemplateNode[]
  edges: WorkflowTemplateEdge[]
}

export type WorkflowTemplate = {
  templateId: string
  ownerKey: string
  name: string
  description: string
  graph: WorkflowTemplateGraph
  createdAt: string | null
  updatedAt: string | null
}

export type WorkflowTemplateListResponse = {
  items: WorkflowTemplate[]
  totalCount: number
}

export async function listWorkflowTemplates(): Promise<WorkflowTemplateListResponse> {
  const { data } = await aiAxiosInstance.get<WorkflowTemplateListResponse>('/workflow-templates')
  return data
}

export async function getWorkflowTemplate(templateId: string): Promise<WorkflowTemplate> {
  const { data } = await aiAxiosInstance.get<WorkflowTemplate>(
    `/workflow-templates/${encodeURIComponent(templateId)}`,
  )
  return data
}

export async function createWorkflowTemplate(payload: {
  name: string
  description?: string
  graph: WorkflowTemplateGraph
}): Promise<WorkflowTemplate> {
  const { data } = await aiAxiosInstance.post<WorkflowTemplate>('/workflow-templates', {
    name: payload.name,
    description: payload.description ?? '',
    graph: payload.graph,
  })
  return data
}

export async function updateWorkflowTemplate(
  templateId: string,
  payload: { name?: string; description?: string; graph?: WorkflowTemplateGraph },
): Promise<WorkflowTemplate> {
  const { data } = await aiAxiosInstance.put<WorkflowTemplate>(
    `/workflow-templates/${encodeURIComponent(templateId)}`,
    payload,
  )
  return data
}

export async function deleteWorkflowTemplate(templateId: string): Promise<void> {
  await aiAxiosInstance.delete(`/workflow-templates/${encodeURIComponent(templateId)}`)
}

export async function instantiateWorkflowTemplate(
  templateId: string,
  sessionId: string,
): Promise<{ workIds: string[] }> {
  const { data } = await aiAxiosInstance.post<{ workIds: string[] }>(
    `/workflow-templates/${encodeURIComponent(templateId)}/instantiate`,
    { sessionId },
  )
  return data
}
