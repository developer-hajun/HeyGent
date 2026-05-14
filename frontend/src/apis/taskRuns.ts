import aiAxiosInstance from './aiAxiosInstance'
import type { RawTaskRun, TaskRunFlowResponse } from '@/types/taskRuns'

type TaskRunListResponse = {
  items?: RawTaskRun[]
}

export async function listTaskRuns(input: {
  sessionId: string
  pageSize?: number
  status?: string
}): Promise<RawTaskRun[]> {
  const { data } = await aiAxiosInstance.get<TaskRunListResponse>('/taskRuns', {
    params: {
      sessionId: input.sessionId,
      pageSize: input.pageSize ?? 20,
      status: input.status ?? 'ALL',
    },
  })
  return data.items ?? []
}

export async function getTaskRun(taskRunId: string): Promise<RawTaskRun> {
  const { data } = await aiAxiosInstance.get<RawTaskRun>(`/taskRuns/${taskRunId}`)
  return data
}

export async function getTaskRunFlow(taskRunId: string): Promise<TaskRunFlowResponse> {
  const { data } = await aiAxiosInstance.get<TaskRunFlowResponse>(`/taskRuns/${taskRunId}/flow`)
  return data
}
