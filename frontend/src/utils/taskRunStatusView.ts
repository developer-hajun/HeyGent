import { type RawTaskEventPayload, isJsonObject } from '@/realtime/aiRealtimeTypes'
import type {
  ActivityItemView,
  RawApproval,
  RawStepRun,
  RawTaskRun,
  TaskRunDetailSummaryView,
  TaskRunDisplayContext,
  TaskRunStatusTone,
  TaskRunSummaryView,
} from '@/types/taskRuns'
import { getLastTaskRunSequence, sortTaskRunEvents } from './taskRunEvents'

const EVENT_STATUS_TEXT: Record<string, string> = {
  accepted: '요청 접수됨',
  'task.created': '요청 확인 중',
  'task.started': '답변 준비 중',
  'task.updated': '진행 상황 갱신됨',
  'task.completed': '답변 완료',
  'task.failed': '답변 실패',
  'task.canceled': '요청 취소됨',
  'task.waiting': '확인 대기 중',
  'step.created': '진행 단계 준비',
  'step.started': '진행 단계 실행 중',
  'step.completed': '진행 단계 완료',
  'step.failed': '진행 단계 실패',
  'step.canceled': '진행 단계 취소됨',
  'step.waiting': '진행 단계 확인 대기',
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
    case 'accepted':
    case 'task.created':
    case 'task.started':
    case 'step.started':
    case 'tool.started':
    case 'search.started':
    case 'session.message.delta':
      return 'running'
    case 'WAITING':
    case 'PENDING':
    case 'BLOCKED':
    case 'approval.required':
    case 'task.waiting':
    case 'step.waiting':
      return 'waiting'
    case 'COMPLETED':
    case 'task.completed':
    case 'step.completed':
    case 'tool.completed':
    case 'search.completed':
    case 'session.message.completed':
      return 'completed'
    case 'FAILED':
    case 'CANCELLED':
    case 'CANCELED':
    case 'task.failed':
    case 'task.canceled':
    case 'step.failed':
    case 'step.canceled':
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

export const isLiveTaskRunStatus = (status?: string | null) =>
  status === 'PENDING' ||
  status === 'RUNNING' ||
  status === 'WAITING' ||
  status === 'accepted' ||
  status === 'task.created' ||
  status === 'task.started' ||
  status === 'task.updated' ||
  status === 'task.waiting' ||
  status === 'step.created' ||
  status === 'step.started' ||
  status === 'step.waiting' ||
  status === 'tool.started' ||
  status === 'search.started' ||
  status === 'session.message.delta'

export const toActivityItemView = (event: RawTaskEventPayload): ActivityItemView => {
  const statusKey = event.event_type ?? event.status
  const eventTitle = toTaskRunEventTitle(event.event_type)
  const payloadTitle = getTaskRunEventPayloadTitle(event)
  const summaryTitle = getMeaningfulTaskEventSummary(event.summary_message)
  const preferPayloadTitle = shouldPreferPayloadTitle(event.event_type)
  const title =
    (preferPayloadTitle ? payloadTitle : summaryTitle) ??
    (preferPayloadTitle ? summaryTitle : payloadTitle) ??
    eventTitle ??
    toTaskRunStatusText(statusKey)

  return {
    id: event.event_id,
    taskRunId: event.task_run_id,
    stepRunId: typeof event.step_run_id === 'string' ? event.step_run_id : undefined,
    title,
    statusText: toTaskRunStatusText(statusKey),
    tone: toTaskRunStatusTone(statusKey),
    sequence: typeof event.sequence === 'number' ? event.sequence : undefined,
    occurredAt: typeof event.occurred_at === 'string' ? event.occurred_at : undefined,
    displayContext: getDisplayContext(event.payload),
    raw: event,
  }
}

const getDisplayContext = (payload: unknown): TaskRunDisplayContext | undefined => {
  if (!isJsonObject(payload) || !isJsonObject(payload.displayContext)) {
    return undefined
  }
  const context = payload.displayContext
  return isJsonObject(context.assigneeAgent) && isJsonObject(context.actorAgent)
    ? (context as TaskRunDisplayContext)
    : undefined
}

export const toTaskRunSummaryView = (
  taskRun: RawTaskRun | undefined,
  events: RawTaskEventPayload[] = [],
): TaskRunSummaryView => {
  const sortedEvents = sortTaskRunEvents(
    events.filter((event) => !isInternalStepAnchorEvent(event)),
  )
  const lastEvent = sortedEvents.at(-1)
  const status = taskRun?.status ?? lastEvent?.status ?? lastEvent?.event_type
  const title = getTaskRunDisplayTitle(taskRun) ?? lastEvent?.summary_message ?? '답변 진행'

  return {
    id: taskRun?.task_run_id ?? lastEvent?.task_run_id ?? 'unknown',
    title,
    statusText: toTaskRunStatusText(status),
    tone: toTaskRunStatusTone(status),
    lastSequence: getLastTaskRunSequence(events) ?? getTaskRunLastSequence(taskRun),
    raw: taskRun,
  }
}

export type TaskRunDetailSummaryInput = {
  taskRun?: RawTaskRun
  stepRuns?: RawStepRun[]
  approvals?: RawApproval[]
  events?: RawTaskEventPayload[]
  replayNeeded?: boolean
  recovering?: boolean
  recoveryAfterSequence?: number
}

export const toTaskRunDetailSummaryView = ({
  taskRun,
  stepRuns = [],
  approvals = [],
  events = [],
  replayNeeded = false,
  recovering = false,
  recoveryAfterSequence,
}: TaskRunDetailSummaryInput): TaskRunDetailSummaryView => {
  const visibleEvents = events.filter((event) => !isInternalStepAnchorEvent(event))
  const visibleStepRuns = stepRuns.filter((stepRun) => !isInternalStepAnchorStepRun(stepRun))
  const sortedEvents = sortTaskRunEvents(visibleEvents)
  const latestEvent = sortedEvents.at(-1)
  const latestStepRun = selectLatestStepRun(taskRun, visibleStepRuns)
  const pendingApproval = selectPendingApproval(approvals)
  const summary = toTaskRunSummaryView(taskRun, sortedEvents)

  return {
    ...summary,
    latestStepRun,
    latestEvent,
    pendingApproval,
    activityItems: sortedEvents.map(toActivityItemView),
    replayNeeded,
    recovering,
    recoveryAfterSequence,
  }
}

export const isInternalStepAnchorEvent = (event: RawTaskEventPayload) =>
  isInternalStepAnchorPayload(event.payload)

export const isInternalStepAnchorStepRun = (stepRun: RawStepRun) => {
  if (stepRun.internal_step_anchor === true || stepRun.internalStepAnchor === true) {
    return true
  }
  const inputPayload = isJsonObject(stepRun.input_payload) ? stepRun.input_payload : undefined
  return (
    inputPayload?.progress_fallback_step === true ||
    inputPayload?.internal_step_anchor === true ||
    inputPayload?.internalStepAnchor === true
  )
}

const isInternalStepAnchorPayload = (payload: unknown) =>
  isJsonObject(payload) &&
  (payload.internal_step_anchor === true ||
    payload.internalStepAnchor === true ||
    payload.step_visibility === 'internal' ||
    payload.stepVisibility === 'internal')

const selectLatestStepRun = (taskRun: RawTaskRun | undefined, stepRuns: RawStepRun[]) => {
  const currentStepRunId =
    typeof taskRun?.current_step_run_id === 'string'
      ? taskRun.current_step_run_id
      : typeof taskRun?.currentStepRunId === 'string'
        ? taskRun.currentStepRunId
        : undefined

  if (currentStepRunId !== undefined) {
    const currentStepRun = stepRuns.find((stepRun) => stepRun.step_run_id === currentStepRunId)
    if (currentStepRun !== undefined) {
      return currentStepRun
    }
  }

  return [...stepRuns].sort(compareStepRuns).at(-1)
}

const selectPendingApproval = (approvals: RawApproval[]) =>
  [...approvals].sort(compareApprovals).find((approval) => approval.status === 'PENDING') ??
  [...approvals].sort(compareApprovals).at(-1)

const compareStepRuns = (first: RawStepRun, second: RawStepRun) => {
  const firstStepOrder = getStepRunOrder(first)
  const secondStepOrder = getStepRunOrder(second)
  if (firstStepOrder !== undefined && secondStepOrder !== undefined) {
    return firstStepOrder - secondStepOrder
  }

  const firstSequence = typeof first.sequence === 'number' ? first.sequence : undefined
  const secondSequence = typeof second.sequence === 'number' ? second.sequence : undefined

  if (firstSequence !== undefined && secondSequence !== undefined) {
    return firstSequence - secondSequence
  }

  return (
    getComparableTime(first.started_at ?? first.completed_at) -
    getComparableTime(second.started_at ?? second.completed_at)
  )
}

const getStepRunOrder = (stepRun: RawStepRun) => {
  if (typeof stepRun.step_order === 'number' && Number.isFinite(stepRun.step_order)) {
    return stepRun.step_order
  }
  if (typeof stepRun.stepOrder === 'number' && Number.isFinite(stepRun.stepOrder)) {
    return stepRun.stepOrder
  }
  return undefined
}

const compareApprovals = (first: RawApproval, second: RawApproval) =>
  getComparableTime(first.created_at) - getComparableTime(second.created_at)

const getTaskRunLastSequence = (taskRun: RawTaskRun | undefined) => {
  if (typeof taskRun?.last_sequence === 'number' && Number.isFinite(taskRun.last_sequence)) {
    return taskRun.last_sequence
  }

  return typeof taskRun?.lastSequence === 'number' && Number.isFinite(taskRun.lastSequence)
    ? taskRun.lastSequence
    : undefined
}

const getTaskRunDisplayTitle = (taskRun: RawTaskRun | undefined) => {
  // 서버가 저장한 입력값이 있으면 디버깅할 때 바로 질문 원문을 볼 수 있게 우선 표시한다.
  const prompt =
    typeof taskRun?.input_payload === 'object' &&
    taskRun.input_payload !== null &&
    'prompt' in taskRun.input_payload &&
    typeof taskRun.input_payload.prompt === 'string'
      ? taskRun.input_payload.prompt.trim()
      : ''

  if (prompt !== '') {
    return extractOriginalPrompt(prompt)
  }

  return taskRun?.title ?? taskRun?.goal
}

const extractOriginalPrompt = (prompt: string) => {
  const marker = '원래 사용자 요청:'
  if (!prompt.includes(marker)) {
    return prompt
  }

  return prompt.split(marker).at(-1)?.trim() || prompt
}

const toTaskRunEventTitle = (eventType?: string | null) => {
  // 같은 RUNNING 상태라도 이벤트 타입별로 사용자가 보는 진행 문구는 다르게 보여준다.
  switch (eventType) {
    case 'task.created':
      return '요청 내용을 확인했습니다.'
    case 'task.started':
      return '답변 준비를 시작했습니다.'
    case 'step.created':
      return '진행 단계 준비'
    case 'step.started':
      return '진행 단계 실행 중'
    case 'step.completed':
      return '진행 단계 완료'
    case 'tool.started':
      return '도구 실행 중'
    case 'tool.completed':
      return '도구 실행 완료'
    case 'search.started':
      return '자료 확인 중'
    case 'search.completed':
      return '자료 확인 완료'
    case 'task.completed':
      return '답변 완료'
    case 'session.message.delta':
      return '답변 작성 중'
    case 'session.message.completed':
      return '답변 작성 완료'
    case 'task.updated':
      return '진행 상황이 업데이트되었습니다.'
    case 'task.waiting':
    case 'step.waiting':
      return '추가 확인을 기다리고 있습니다.'
    case 'task.failed':
    case 'step.failed':
      return '처리 중 문제가 발생했습니다.'
    case 'task.canceled':
    case 'step.canceled':
      return '요청이 취소되었습니다.'
    default:
      return undefined
  }
}

const getMeaningfulTaskEventSummary = (value?: string | null) => {
  const text = typeof value === 'string' ? value.trim() : ''
  if (
    text === '' ||
    text === '답변을 준비하는 중입니다.' ||
    text === '답변 준비 중' ||
    text === '작업 중'
  ) {
    return undefined
  }
  return text
}

const shouldPreferPayloadTitle = (eventType?: string | null) =>
  typeof eventType === 'string' &&
  (eventType.startsWith('tool.') || eventType.startsWith('search.'))

const getTaskRunEventPayloadTitle = (event: RawTaskEventPayload) =>
  pickTaskRunEventString(event.payload, [
    'step_title',
    'stepTitle',
    'title',
    'goal',
    'name',
    'label',
    'tool_name',
    'toolName',
    'query',
  ]) ??
  pickNestedTaskRunEventString(
    event.payload,
    ['input', 'args'],
    ['path', 'query', 'pattern', 'command', 'title', 'content'],
  ) ??
  pickNestedTaskRunEventString(
    event.payload,
    ['result', 'output'],
    ['path', 'query', 'pattern', 'summary', 'stdout', 'text'],
  ) ??
  pickTaskRunEventString(event.detail_json, [
    'step_title',
    'stepTitle',
    'title',
    'goal',
    'name',
    'label',
    'tool_name',
    'toolName',
    'query',
  ])

const pickNestedTaskRunEventString = (value: unknown, containerKeys: string[], keys: string[]) => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return undefined
  }

  const payload = value as Record<string, unknown>
  for (const containerKey of containerKeys) {
    const candidate = pickTaskRunEventString(payload[containerKey], keys)
    if (candidate !== undefined) {
      return candidate
    }
  }

  return undefined
}

const pickTaskRunEventString = (value: unknown, keys: string[]) => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return undefined
  }

  const payload = value as Record<string, unknown>
  for (const key of keys) {
    const candidate = payload[key]
    if (typeof candidate === 'string' && candidate.trim() !== '') {
      return candidate.trim()
    }
  }

  return undefined
}

const getComparableTime = (value?: string | null) => {
  if (typeof value !== 'string') {
    return 0
  }
  const time = Date.parse(value)
  return Number.isFinite(time) ? time : 0
}
