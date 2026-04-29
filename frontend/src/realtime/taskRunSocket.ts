import { useAuthStore } from '@/store/useAuthStore'

const DEFAULT_AI_WS_BASE_URL = 'ws://localhost:8000/api/v1/gateway/ws'

export type AuthOkEvent = {
  type: 'auth.ok'
  userId: string
}

export type AuthFailedEvent = {
  type: 'auth.failed'
}

export type AuthRequiredEvent = {
  type: 'auth.required'
}

export type SubscribedEvent = {
  type: 'subscribed'
  task_run_id: string
}

export type TaskEventData = {
  event_id: string
  event_type: string
  task_run_id: string
  step_run_id: string | null
  producer: string
  occurred_at: string
  status: string | null
  summary_message: string | null
  payload: Record<string, unknown>
}

export type TaskEvent = {
  type: 'task.event'
  data: TaskEventData
}

export type PongEvent = {
  type: 'pong'
}

export type TaskRunSocketEvent =
  | AuthOkEvent
  | AuthFailedEvent
  | AuthRequiredEvent
  | SubscribedEvent
  | TaskEvent
  | PongEvent

export type TaskRunSocketEventHandler = (event: TaskRunSocketEvent) => void

export type CreateTaskRunSocketOptions = {
  accessToken?: string | null
  url?: string
}

export type TaskRunSocketClient = {
  socket: WebSocket
  isAuthenticated: () => boolean
  onMessage: (handler: TaskRunSocketEventHandler) => () => void
  subscribeTask: (taskRunId: string) => void
  subscribeAll: () => void
  ping: () => void
  close: (code?: number, reason?: string) => void
}

type RawTaskRunSocketEvent = {
  type?: unknown
  [key: string]: unknown
}

const getAiWebSocketBaseUrl = () => import.meta.env.VITE_AI_WS_BASE_URL || DEFAULT_AI_WS_BASE_URL

const getAccessToken = (options: CreateTaskRunSocketOptions) => {
  if ('accessToken' in options) {
    return options.accessToken
  }
  return useAuthStore.getState().accessToken
}

const requireAccessToken = (options: CreateTaskRunSocketOptions) => {
  const accessToken = getAccessToken(options)

  if (typeof accessToken !== 'string' || accessToken.trim() === '') {
    throw new Error('AI WebSocket 연결에 사용할 accessToken이 없습니다.')
  }

  return accessToken
}

const parseObject = (data: string): RawTaskRunSocketEvent | null => {
  try {
    const parsed: unknown = JSON.parse(data)
    return typeof parsed === 'object' && parsed !== null ? (parsed as RawTaskRunSocketEvent) : null
  } catch {
    return null
  }
}

export const parseTaskRunSocketEvent = (data: string): TaskRunSocketEvent | null => {
  const event = parseObject(data)

  switch (event?.type) {
    case 'auth.ok':
      return typeof event.userId === 'string' ? { type: 'auth.ok', userId: event.userId } : null
    case 'auth.failed':
      return { type: 'auth.failed' }
    case 'auth.required':
      return { type: 'auth.required' }
    case 'subscribed':
      return typeof event.task_run_id === 'string'
        ? { type: 'subscribed', task_run_id: event.task_run_id }
        : null
    case 'task.event':
      return isTaskEventData(event.data) ? { type: 'task.event', data: event.data } : null
    case 'pong':
      return { type: 'pong' }
    default:
      return null
  }
}

export const createTaskRunSocket = (
  options: CreateTaskRunSocketOptions = {},
): TaskRunSocketClient => {
  const accessToken = requireAccessToken(options)
  const socket = new WebSocket(options.url || getAiWebSocketBaseUrl())
  const handlers = new Set<TaskRunSocketEventHandler>()
  let authenticated = false

  socket.addEventListener('open', () => {
    // 브라우저 WebSocket 생성자는 Authorization header를 직접 지정할 수 없다.
    // 그래서 연결 직후 첫 메시지로 accessToken을 보내 서버가 같은 연결을 인증하게 한다.
    socket.send(JSON.stringify({ action: 'auth', accessToken }))
  })

  socket.addEventListener('message', (message) => {
    if (typeof message.data !== 'string') {
      return
    }

    const event = parseTaskRunSocketEvent(message.data)
    if (event === null) {
      return
    }

    if (event.type === 'auth.ok') {
      authenticated = true
    }

    handlers.forEach((handler) => handler(event))
  })

  const send = (payload: Record<string, unknown>) => {
    socket.send(JSON.stringify(payload))
  }

  const requireAuthenticated = () => {
    if (!authenticated) {
      throw new Error('AI WebSocket 인증 완료 전에는 구독할 수 없습니다.')
    }
  }

  return {
    socket,
    isAuthenticated: () => authenticated,
    onMessage: (handler) => {
      handlers.add(handler)
      return () => handlers.delete(handler)
    },
    subscribeTask: (taskRunId) => {
      requireAuthenticated()
      send({ action: 'subscribe', task_run_id: taskRunId })
    },
    subscribeAll: () => {
      requireAuthenticated()
      send({ action: 'subscribe_all' })
    },
    ping: () => {
      send({ action: 'ping' })
    },
    close: (code, reason) => {
      socket.close(code, reason)
    },
  }
}

const isTaskEventData = (value: unknown): value is TaskEventData => {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const data = value as Partial<TaskEventData>

  return (
    typeof data.event_id === 'string' &&
    typeof data.event_type === 'string' &&
    typeof data.task_run_id === 'string' &&
    (typeof data.step_run_id === 'string' || data.step_run_id === null) &&
    typeof data.producer === 'string' &&
    typeof data.occurred_at === 'string' &&
    (typeof data.status === 'string' || data.status === null) &&
    (typeof data.summary_message === 'string' || data.summary_message === null) &&
    typeof data.payload === 'object' &&
    data.payload !== null
  )
}
