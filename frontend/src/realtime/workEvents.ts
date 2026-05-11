import type { WorkCreateResponse, WorkItem } from '@/types/work'

export type WorkRealtimeEvent =
  | { type: 'work.created'; work: WorkItem; taskRunId: string | null; taskStatus: string | null }
  | { type: 'work.updated'; work: WorkItem }

export function toWorkCreatedEvent(response: WorkCreateResponse): WorkRealtimeEvent {
  return {
    type: 'work.created',
    work: { ...response.work, taskStatus: response.taskStatus },
    taskRunId: response.taskRunId,
    taskStatus: response.taskStatus,
  }
}
