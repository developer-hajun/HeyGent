import type { RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'
import type {
  ActivityItemView,
  RawTaskRun,
  TaskRunStatusTone,
  TaskRunSummaryView,
} from '@/types/taskRuns'
import { getLastTaskRunSequence } from './taskRunEvents'

const EVENT_STATUS_TEXT: Record<string, string> = {
  accepted: '요청 접수됨',
  'step.started': '작업 중',
  'step.completed': '단계 완료',
  'tool.started': '도구 실행 중',
  'tool.completed': '도구 실행 완료',
  'search.started': '자료 확인 중',
  'search.completed': '자료 확인 완료',
  'approval.required': '확인 필요',
  'session.message.delta': '응답 작성 중',
  'session.message.completed': '응답 완료',
}

const STATUS_TEXT: Record<string, string> = {
  PENDING: '대기 중',
  RUNNING: '작업 중',
  WAITING: '확인 필요',
  COMPLETED: '완료',
  FAILED: '오류 발생',
  CANCELLED: '취소됨',
  reconnecting: '연결 복구 중',
}

export const toTaskRunStatusTone = (status?: string | null): TaskRunStatusTone => {
  switch (status) {
    case 'RUNNING':
    case 'PENDING':
    case 'accepted':
    case 'step.started':
    case 'tool.started':
    case 'search.started':
    case 'session.message.delta':
      return 'running'
    case 'WAITING':
    case 'approval.required':
      return 'waiting'
    case 'COMPLETED':
    case 'step.completed':
    case 'tool.completed':
    case 'search.completed':
    case 'session.message.completed':
      return 'completed'
    case 'FAILED':
    case 'CANCELLED':
      return 'failed'
    default:
      return 'idle'
  }
}

export const toTaskRunStatusText = (status?: string | null) => {
  if (status === undefined || status === null || status.trim() === '') {
    return '상태 확인 중'
  }
  return STATUS_TEXT[status] ?? EVENT_STATUS_TEXT[status] ?? '작업 중'
}

export const toActivityItemView = (event: RawTaskEventPayload): ActivityItemView => {
  const statusKey = event.status ?? event.event_type
  const title =
    event.summary_message ??
    (typeof event.detail_json === 'object' && event.detail_json !== null
      ? '세부 작업 진행 중'
      : toTaskRunStatusText(statusKey))

  return {
    id: event.event_id,
    taskRunId: event.task_run_id,
    stepRunId: typeof event.step_run_id === 'string' ? event.step_run_id : undefined,
    title,
    statusText: toTaskRunStatusText(statusKey),
    tone: toTaskRunStatusTone(statusKey),
    sequence: typeof event.sequence === 'number' ? event.sequence : undefined,
    occurredAt: typeof event.occurred_at === 'string' ? event.occurred_at : undefined,
    raw: event,
  }
}

export const toTaskRunSummaryView = (
  taskRun: RawTaskRun | undefined,
  events: RawTaskEventPayload[] = [],
): TaskRunSummaryView => {
  const lastEvent = events.at(-1)
  const status = taskRun?.status ?? lastEvent?.status ?? lastEvent?.event_type
  const title = taskRun?.title ?? taskRun?.goal ?? lastEvent?.summary_message ?? '작업'

  return {
    id: taskRun?.task_run_id ?? lastEvent?.task_run_id ?? 'unknown',
    title,
    statusText: toTaskRunStatusText(status),
    tone: toTaskRunStatusTone(status),
    lastSequence: getLastTaskRunSequence(events),
    raw: taskRun,
  }
}
