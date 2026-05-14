type MessageIdentity = {
  id?: string
  sessionId?: string
  taskRunId?: string
  clientMessageId?: string
  role?: string
  status?: string
}

type SessionRunState = {
  active_task_run_id?: string | null
  activeTaskRunId?: string | null
  last_task_run_status?: string | null
  lastTaskRunStatus?: string | null
  updated_at?: string | null
  updatedAt?: string | null
}

const LIVE_MESSAGE_STATUSES = new Set(['optimistic', 'streaming', 'waiting'])
const TERMINAL_TASK_RUN_STATUSES = new Set([
  'COMPLETED',
  'FAILED',
  'CANCELED',
  'CANCELLED',
  'task.completed',
  'task.failed',
  'task.canceled',
  'task.cancelled',
])
const RUNNING_TASK_RUN_STATUSES = new Set(['PENDING', 'RUNNING', 'WAITING'])

export function mergeLiveMessagesIntoPersistedList<T extends MessageIdentity>(
  persistedMessages: T[],
  previousMessages: T[],
  sessionId: string,
) {
  const missingLiveMessages = previousMessages.filter(
    (message) =>
      message.sessionId === sessionId &&
      isLiveMessage(message) &&
      !persistedMessages.some((persisted) => isSameMessage(persisted, message)),
  )

  return [...persistedMessages, ...missingLiveMessages]
}

export function resolveCompletedSessionTaskStatus(status?: string) {
  return status ?? 'COMPLETED'
}

export function reconcileSessionRunState<T extends SessionRunState>(
  previousSession: T | undefined,
  incomingSession: T,
) {
  if (previousSession === undefined) {
    return incomingSession
  }

  const previousStatus = getTaskRunStatus(previousSession)
  const incomingStatus = getTaskRunStatus(incomingSession)
  const previousUpdatedAt = getSessionUpdatedTime(previousSession)
  const incomingUpdatedAt = getSessionUpdatedTime(incomingSession)

  if (
    previousUpdatedAt > incomingUpdatedAt &&
    isTerminalTaskRunStatus(previousStatus) &&
    hasPossiblyStaleRunningState(incomingSession, incomingStatus)
  ) {
    return {
      ...incomingSession,
      active_task_run_id: null,
      last_task_run_status: previousStatus,
    }
  }

  return incomingSession
}

export function shouldClearSessionRunFromPersistedMessages(
  session: SessionRunState | undefined,
  messages: MessageIdentity[],
) {
  if (session === undefined) {
    return false
  }

  const activeTaskRunId = getActiveTaskRunId(session)
  const taskRunStatus = getTaskRunStatus(session)
  if (activeTaskRunId === undefined || isTerminalTaskRunStatus(taskRunStatus)) {
    return false
  }

  if (
    messages.some(
      (message) =>
        message.role === 'assistant' &&
        message.status === 'completed' &&
        message.taskRunId === activeTaskRunId,
    )
  ) {
    return true
  }

  const latestMessage = messages.at(-1)
  return (
    hasPossiblyStaleRunningState(session, taskRunStatus) &&
    !messages.some(isLiveMessage) &&
    latestMessage?.role === 'assistant' &&
    (latestMessage.status === 'completed' || latestMessage.status === 'failed')
  )
}

function isLiveMessage(message: MessageIdentity) {
  return typeof message.status === 'string' && LIVE_MESSAGE_STATUSES.has(message.status)
}

function isSameMessage(first: MessageIdentity, second: MessageIdentity) {
  if (hasSharedString(first.id, second.id)) {
    return true
  }
  if (hasSharedString(first.taskRunId, second.taskRunId) && first.role === second.role) {
    return true
  }
  return (
    hasSharedString(first.clientMessageId, second.clientMessageId) && first.role === second.role
  )
}

function hasSharedString(first?: string, second?: string) {
  return first !== undefined && first.trim() !== '' && first === second
}

function hasPossiblyStaleRunningState(session: SessionRunState, status?: string) {
  const activeTaskRunId = getActiveTaskRunId(session)
  if (status === undefined) {
    return activeTaskRunId !== undefined
  }
  return RUNNING_TASK_RUN_STATUSES.has(status)
}

function isTerminalTaskRunStatus(status?: string) {
  return status !== undefined && TERMINAL_TASK_RUN_STATUSES.has(status)
}

function getActiveTaskRunId(session: SessionRunState) {
  return stringValue(session.active_task_run_id) ?? stringValue(session.activeTaskRunId)
}

function getTaskRunStatus(session: SessionRunState) {
  return stringValue(session.last_task_run_status) ?? stringValue(session.lastTaskRunStatus)
}

function getSessionUpdatedTime(session: SessionRunState) {
  const rawTime = stringValue(session.updated_at) ?? stringValue(session.updatedAt)
  if (rawTime === undefined) {
    return 0
  }
  const time = new Date(rawTime).getTime()
  return Number.isFinite(time) ? time : 0
}

function stringValue(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value : undefined
}
