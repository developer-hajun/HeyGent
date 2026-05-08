import {
  AI_REALTIME_PROTOCOL_VERSION,
  type AiRealtimeRawFrame,
  type AuthOkPayload,
  type JsonObject,
  type RawTaskEventPayload,
  getFramePayload,
  getStringField,
  parseAiRealtimeRawFrame,
} from './aiRealtimeTypes'
import { useAuthStore } from '@/store/useAuthStore'

export type AuthOkEvent = {
  type: 'auth.ok'
  userId: string
  workspaceKey?: string
  raw: AiRealtimeRawFrame
}

export type AuthFailedEvent = {
  type: 'auth.failed'
  raw: AiRealtimeRawFrame
}

export type AuthRequiredEvent = {
  type: 'auth.required'
  raw: AiRealtimeRawFrame
}

export type SubscribedEvent = {
  type: 'subscribed'
  taskRunId: string
  raw: AiRealtimeRawFrame
}

export type TaskEvent = {
  type: 'task.event'
  data: RawTaskEventPayload
  raw: AiRealtimeRawFrame
}

export type PongEvent = {
  type: 'pong'
  raw: AiRealtimeRawFrame
}

export type TaskRunSocketEvent =
  | AuthOkEvent
  | AuthFailedEvent
  | AuthRequiredEvent
  | SubscribedEvent
  | TaskEvent
  | PongEvent

export type TaskRunSocketEventHandler = (event: TaskRunSocketEvent) => void

export type TaskRunSocketRawHandler = (frame: AiRealtimeRawFrame) => void

export type SubscribeTaskOptions = {
  lastSequence?: number
}

export type CreateTaskRunSocketOptions = {
  accessToken?: string | null
  workspaceKey?: string | null
  url?: string
}

export type TaskRunSocketCloseHandler = (event: CloseEvent) => void
export type TaskRunSocketErrorHandler = (event: Event) => void
export type TaskRunSocketOpenHandler = (event: Event) => void

export type TaskRunSocketClient = {
  socket: WebSocket
  isAuthenticated: () => boolean
  isOpen: () => boolean
  getReadyState: () => number
  onMessage: (handler: TaskRunSocketEventHandler) => () => void
  onRawMessage: (handler: TaskRunSocketRawHandler) => () => void
  onOpen: (handler: TaskRunSocketOpenHandler) => () => void
  onClose: (handler: TaskRunSocketCloseHandler) => () => void
  onError: (handler: TaskRunSocketErrorHandler) => () => void
  sendJson: (payload: JsonObject) => void
  subscribeTask: (taskRunId: string, options?: SubscribeTaskOptions) => void
  subscribeAll: () => void
  ping: () => void
  close: (code?: number, reason?: string) => void
}

const getAiWebSocketBaseUrl = (options: CreateTaskRunSocketOptions) => {
  const baseUrl = options.url ?? import.meta.env.VITE_AI_WS_BASE_URL

  if (typeof baseUrl !== 'string' || baseUrl.trim() === '') {
    throw new Error('VITE_AI_WS_BASE_URL이 설정되지 않아 AI WebSocket에 연결할 수 없습니다.')
  }

  return baseUrl
}

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

const getWorkspaceKey = (options: CreateTaskRunSocketOptions) => {
  if (typeof options.workspaceKey !== 'string' || options.workspaceKey.trim() === '') {
    return undefined
  }

  return options.workspaceKey
}

export const parseTaskRunSocketEvent = (data: string): TaskRunSocketEvent | null => {
  const frame = parseAiRealtimeRawFrame(data)
  if (frame === null) {
    return null
  }
  return parseTaskRunSocketFrame(frame)
}

export const parseTaskRunSocketFrame = (frame: AiRealtimeRawFrame): TaskRunSocketEvent | null => {
  switch (frame.type) {
    case 'auth.ok':
      return parseAuthOkEvent(frame)
    case 'auth.failed':
      return { type: 'auth.failed', raw: frame }
    case 'auth.required':
      return { type: 'auth.required', raw: frame }
    case 'subscribed':
      return parseSubscribedEvent(frame)
    case 'task.event':
      return parseTaskEvent(frame)
    case 'pong':
      return { type: 'pong', raw: frame }
    default:
      return null
  }
}

export const createTaskRunSocket = (
  options: CreateTaskRunSocketOptions = {},
): TaskRunSocketClient => {
  const accessToken = requireAccessToken(options)
  const workspaceKey = getWorkspaceKey(options)
  const socket = new WebSocket(getAiWebSocketBaseUrl(options))
  const handlers = new Set<TaskRunSocketEventHandler>()
  const rawHandlers = new Set<TaskRunSocketRawHandler>()
  const openHandlers = new Set<TaskRunSocketOpenHandler>()
  const closeHandlers = new Set<TaskRunSocketCloseHandler>()
  const errorHandlers = new Set<TaskRunSocketErrorHandler>()
  let authenticated = false

  const sendJson = (payload: JsonObject) => {
    if (socket.readyState !== WebSocket.OPEN) {
      throw new Error('AI WebSocket이 open 상태가 아니어서 메시지를 보낼 수 없습니다.')
    }
    socket.send(JSON.stringify(payload))
  }

  socket.addEventListener('open', (event) => {
    openHandlers.forEach((handler) => handler(event))
    // 브라우저 WebSocket은 Authorization header를 못 붙인다.
    // 서버 전환기 호환을 위해 envelope payload와 기존 top-level token을 함께 보낸다.
    sendJson({
      protocolVersion: AI_REALTIME_PROTOCOL_VERSION,
      type: 'auth.start',
      sentAt: new Date().toISOString(),
      payload: { accessToken, workspaceKey },
      accessToken,
      workspaceKey,
    })
  })

  socket.addEventListener('message', (message) => {
    if (typeof message.data !== 'string') {
      return
    }

    const frame = parseAiRealtimeRawFrame(message.data)
    if (frame === null) {
      return
    }

    rawHandlers.forEach((handler) => handler(frame))

    const event = parseTaskRunSocketFrame(frame)
    if (event === null) {
      return
    }

    if (event.type === 'auth.ok') {
      authenticated = true
    }

    if (event.type === 'auth.failed' || event.type === 'auth.required') {
      authenticated = false
    }

    handlers.forEach((handler) => handler(event))
  })

  socket.addEventListener('close', (event) => {
    authenticated = false
    closeHandlers.forEach((handler) => handler(event))
  })

  socket.addEventListener('error', (event) => {
    errorHandlers.forEach((handler) => handler(event))
  })

  const requireAuthenticated = () => {
    if (!authenticated) {
      throw new Error('AI WebSocket 인증 완료 전에는 구독할 수 없습니다.')
    }
  }

  return {
    socket,
    isAuthenticated: () => authenticated,
    isOpen: () => socket.readyState === WebSocket.OPEN,
    getReadyState: () => socket.readyState,
    onMessage: (handler) => {
      handlers.add(handler)
      return () => handlers.delete(handler)
    },
    onRawMessage: (handler) => {
      rawHandlers.add(handler)
      return () => rawHandlers.delete(handler)
    },
    onOpen: (handler) => {
      openHandlers.add(handler)
      return () => openHandlers.delete(handler)
    },
    onClose: (handler) => {
      closeHandlers.add(handler)
      return () => closeHandlers.delete(handler)
    },
    onError: (handler) => {
      errorHandlers.add(handler)
      return () => errorHandlers.delete(handler)
    },
    sendJson,
    subscribeTask: (taskRunId, subscribeOptions = {}) => {
      requireAuthenticated()
      sendJson({
        protocolVersion: AI_REALTIME_PROTOCOL_VERSION,
        type: 'subscribe.task',
        sentAt: new Date().toISOString(),
        payload: {
          task_run_id: taskRunId,
          last_sequence: subscribeOptions.lastSequence,
        },
        taskRunId,
        lastSequence: subscribeOptions.lastSequence,
      })
    },
    subscribeAll: () => {
      requireAuthenticated()
      sendJson({
        protocolVersion: AI_REALTIME_PROTOCOL_VERSION,
        type: 'subscribe.all',
        sentAt: new Date().toISOString(),
        payload: {},
      })
    },
    ping: () => {
      sendJson({
        protocolVersion: AI_REALTIME_PROTOCOL_VERSION,
        type: 'ping',
        sentAt: new Date().toISOString(),
        payload: {},
      })
    },
    close: (code, reason) => {
      socket.close(code, reason)
    },
  }
}

const parseAuthOkEvent = (frame: AiRealtimeRawFrame): AuthOkEvent | null => {
  const payload = getFramePayload(frame) as AuthOkPayload | undefined
  const userId = getStringField(payload, 'user_id', 'userId') ?? getStringField(frame, 'userId')
  const workspaceKey =
    getStringField(payload, 'workspace_key', 'workspaceKey') ??
    getStringField(frame, 'workspaceKey')

  if (userId === undefined) {
    return null
  }

  return { type: 'auth.ok', userId, workspaceKey, raw: frame }
}

const parseSubscribedEvent = (frame: AiRealtimeRawFrame): SubscribedEvent | null => {
  const payload = getFramePayload(frame)
  const taskRunId =
    getStringField(payload, 'task_run_id', 'taskRunId') ??
    getStringField(frame, 'task_run_id', 'taskRunId')

  if (taskRunId === undefined) {
    return null
  }

  return { type: 'subscribed', taskRunId, raw: frame }
}

const parseTaskEvent = (frame: AiRealtimeRawFrame): TaskEvent | null => {
  const payload = getFramePayload(frame)

  if (!isRawTaskEventPayload(payload)) {
    return null
  }

  return { type: 'task.event', data: payload, raw: frame }
}

const isRawTaskEventPayload = (value: unknown): value is RawTaskEventPayload => {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return false
  }

  const data = value as Partial<RawTaskEventPayload>

  return (
    typeof data.event_id === 'string' &&
    typeof data.event_type === 'string' &&
    typeof data.task_run_id === 'string'
  )
}
