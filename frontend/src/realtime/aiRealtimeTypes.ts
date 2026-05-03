// AI realtime protocol version. 서버와 프론트가 같은 envelope 계약을 쓰는지 확인하는 최소 단위다.
export const AI_REALTIME_PROTOCOL_VERSION = 1 as const

export type AiRealtimeProtocolVersion = typeof AI_REALTIME_PROTOCOL_VERSION

export type JsonObject = Record<string, unknown>

export type AiRealtimeConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'open'
  | 'authenticated'
  | 'reconnecting'
  | 'closed'
  | 'error'

export type AiRealtimeAuthStatus = 'anonymous' | 'authenticating' | 'authenticated' | 'failed'

export type AiRealtimeCommandType =
  | 'auth.start'
  | 'ping'
  | 'subscribe.task'
  | 'subscribe.all'
  | 'session.list'
  | 'session.messages.list'
  | 'session.message.create'
  | 'taskRuns.active.list'
  | 'taskRun.snapshot.get'
  | 'taskRun.events.replay'
  | 'taskRun.resume'
  | 'taskRun.cancel'

export type AiRealtimeServerFrameType =
  | 'auth.ok'
  | 'auth.failed'
  | 'auth.required'
  | 'pong'
  | 'subscribed'
  | 'command.error'
  | 'session.list.result'
  | 'session.messages.list.result'
  | 'session.message.accepted'
  | 'session.message.delta'
  | 'session.message.completed'
  | 'session.message.failed'
  | 'taskRuns.active.list.result'
  | 'taskRun.snapshot.result'
  | 'taskRun.events.replay.result'
  | 'taskRun.resume.accepted'
  | 'taskRun.cancel.accepted'
  | 'task.event'

export type AiRealtimeFrameType = AiRealtimeCommandType | AiRealtimeServerFrameType | string

// 서버 실패 응답 원본이다. code/message 외 필드는 서버 shape 그대로 보존한다.
export type AiCommandErrorPayload = {
  code: string
  message: string
  retryable?: boolean
  [key: string]: unknown
}

export type AiRealtimeEnvelopeBase = {
  protocolVersion?: AiRealtimeProtocolVersion | number
  type: AiRealtimeFrameType
  requestId?: string
  sentAt?: string
  serverTime?: string
  payload?: unknown
  data?: unknown
  error?: AiCommandErrorPayload
  [key: string]: unknown
}

export type AiRealtimeClientEnvelope<TPayload extends JsonObject = JsonObject> =
  AiRealtimeEnvelopeBase & {
    protocolVersion: AiRealtimeProtocolVersion
    type: AiRealtimeCommandType
    requestId?: string
    sentAt: string
    payload: TPayload
  }

export type AiRealtimeServerEnvelope<TPayload = unknown> = AiRealtimeEnvelopeBase & {
  type: AiRealtimeServerFrameType
  payload?: TPayload
  data?: TPayload
}

export type AuthStartPayload = {
  accessToken: string
  workspaceKey?: string
}

export type AuthOkPayload = {
  user_id?: string
  workspace_key?: string
  userId?: string
  workspaceKey?: string
  [key: string]: unknown
}

export type SubscribeTaskPayload = {
  task_run_id: string
  last_sequence?: number
}

export type SessionListPayload = {
  cursor?: string
  limit?: number
}

export type SessionMessagesListPayload = {
  sessionId?: string
  session_id?: string
  cursor?: string
  limit?: number
}

export type SessionMessageCreatePayload = {
  sessionId?: string
  session_id?: string
  content: string
  clientMessageId: string
  metadata?: JsonObject
}

export type TaskRunsActiveListPayload = {
  sessionId?: string
  session_id?: string
}

export type TaskRunSnapshotGetPayload = {
  taskRunId?: string
  task_run_id?: string
}

export type TaskRunEventsReplayPayload = {
  taskRunId?: string
  task_run_id?: string
  afterSequence?: number
  after_sequence?: number
}

export type TaskRunResumePayload = {
  taskRunId?: string
  task_run_id?: string
  approvalId?: string
  approval_id?: string
  approvalResponseId?: string
  clientCommandId?: string
  payload: {
    decision?: string
    response?: unknown
    [key: string]: unknown
  }
}

export type TaskRunCancelPayload = {
  taskRunId?: string
  task_run_id?: string
  clientCommandId: string
  reason?: string
}

export type AiRealtimeCommandPayloadMap = {
  'auth.start': AuthStartPayload
  ping: JsonObject
  'subscribe.task': SubscribeTaskPayload
  'subscribe.all': JsonObject
  'session.list': SessionListPayload
  'session.messages.list': SessionMessagesListPayload
  'session.message.create': SessionMessageCreatePayload
  'taskRuns.active.list': TaskRunsActiveListPayload
  'taskRun.snapshot.get': TaskRunSnapshotGetPayload
  'taskRun.events.replay': TaskRunEventsReplayPayload
  'taskRun.resume': TaskRunResumePayload
  'taskRun.cancel': TaskRunCancelPayload
}

// task.event raw payload. snake_case 필드는 디버깅과 서버 frame 비교를 위해 그대로 유지한다.
export type RawTaskEventPayload = {
  event_id: string
  event_type: string
  task_run_id: string
  step_run_id?: string | null
  sequence?: number
  producer?: string | null
  occurred_at?: string | null
  status?: string | null
  summary_message?: string | null
  detail_json?: unknown
  payload?: unknown
  [key: string]: unknown
}

export type RawSessionMessageAcceptedPayload = {
  session_id?: string
  sessionId?: string
  user_message_id?: string
  userMessageId?: string
  assistant_message_id?: string
  assistantMessageId?: string
  task_run_id?: string
  taskRunId?: string
  clientMessageId?: string
  client_message_id?: string
  [key: string]: unknown
}

export type RawSessionMessageDeltaPayload = {
  session_id?: string
  sessionId?: string
  message_id?: string
  messageId?: string
  task_run_id?: string
  taskRunId?: string
  delta?: string
  content_delta?: string
  [key: string]: unknown
}

export type RawSessionMessageCompletedPayload = {
  session_id?: string
  sessionId?: string
  message_id?: string
  messageId?: string
  task_run_id?: string
  taskRunId?: string
  content?: string
  [key: string]: unknown
}

export type RawSessionMessageFailedPayload = {
  session_id?: string
  sessionId?: string
  message_id?: string
  messageId?: string
  user_message_id?: string
  userMessageId?: string
  task_run_id?: string
  taskRunId?: string
  status?: string
  error?: unknown
  [key: string]: unknown
}

export type AiRealtimeRawFrame = AiRealtimeServerEnvelope | AiRealtimeEnvelopeBase

export const isJsonObject = (value: unknown): value is JsonObject =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

export const parseAiRealtimeRawFrame = (data: string): AiRealtimeRawFrame | null => {
  try {
    const parsed: unknown = JSON.parse(data)
    if (!isJsonObject(parsed) || typeof parsed.type !== 'string') {
      return null
    }
    return parsed as AiRealtimeRawFrame
  } catch {
    return null
  }
}

export const getFramePayload = (frame: AiRealtimeRawFrame): unknown => {
  if ('payload' in frame && frame.payload !== undefined) {
    return frame.payload
  }
  return frame.data
}

export const getStringField = (
  value: unknown,
  firstKey: string,
  secondKey?: string,
): string | undefined => {
  if (!isJsonObject(value)) {
    return undefined
  }

  const firstValue = value[firstKey]
  if (typeof firstValue === 'string') {
    return firstValue
  }

  if (secondKey !== undefined && typeof value[secondKey] === 'string') {
    return value[secondKey] as string
  }

  return undefined
}

export const getNumberField = (
  value: unknown,
  firstKey: string,
  secondKey?: string,
): number | undefined => {
  if (!isJsonObject(value)) {
    return undefined
  }

  const firstValue = value[firstKey]
  if (typeof firstValue === 'number' && Number.isFinite(firstValue)) {
    return firstValue
  }

  if (secondKey !== undefined) {
    const secondValue = value[secondKey]
    if (typeof secondValue === 'number' && Number.isFinite(secondValue)) {
      return secondValue
    }
  }

  return undefined
}
