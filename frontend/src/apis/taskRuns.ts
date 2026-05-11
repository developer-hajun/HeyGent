import aiAxiosInstance from './aiAxiosInstance'
import type { RawTaskRun } from '@/types/taskRuns'

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
