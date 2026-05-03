import { create } from 'zustand'
import {
  type AiRealtimeRawFrame,
  type RawSessionMessageAcceptedPayload,
  type RawSessionMessageCompletedPayload,
  type RawSessionMessageDeltaPayload,
  getFramePayload,
  getStringField,
  isJsonObject,
} from '@/realtime/aiRealtimeTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import type {
  ChatMessageView,
  RawAiMessage,
  RawAiSession,
  SessionListResultPayload,
  SessionMessagesListResultPayload,
} from '@/types/aiChat'
import { createClientMessageId } from '@/utils/requestId'

type ChatState = {
  sessionsById: Record<string, RawAiSession>
  messagesBySessionId: Record<string, ChatMessageView[]>
  pendingClientMessageIds: Record<string, string>
  loadingSessionIds: Record<string, boolean>
  lastError: string | null
  fetchSessions: () => Promise<RawAiSession[]>
  fetchMessages: (sessionId: string) => Promise<ChatMessageView[]>
  sendMessage: (input: { sessionId?: string; content: string }) => Promise<AiRealtimeRawFrame>
  handleRealtimeFrame: (frame: AiRealtimeRawFrame) => void
  clearChatState: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessionsById: {},
  messagesBySessionId: {},
  pendingClientMessageIds: {},
  loadingSessionIds: {},
  lastError: null,
  fetchSessions: async () => {
    const frame = await useAiRealtimeStore
      .getState()
      .sendCommand<AiRealtimeRawFrame>('session.list', {})
    const payload = getFramePayload(frame) as SessionListResultPayload
    const sessions = getRawSessionList(payload)

    set((state) => ({
      sessionsById: {
        ...state.sessionsById,
        ...Object.fromEntries(sessions.map((session) => [session.session_id, session])),
      },
      lastError: null,
    }))

    return sessions
  },
  fetchMessages: async (sessionId) => {
    set((state) => ({
      loadingSessionIds: { ...state.loadingSessionIds, [sessionId]: true },
    }))

    try {
      const frame = await useAiRealtimeStore
        .getState()
        .sendCommand<AiRealtimeRawFrame>('session.messages.list', { sessionId })
      const payload = getFramePayload(frame) as SessionMessagesListResultPayload
      const messages = getRawMessageList(payload).map(toChatMessageView)

      set((state) => ({
        messagesBySessionId: { ...state.messagesBySessionId, [sessionId]: messages },
        loadingSessionIds: { ...state.loadingSessionIds, [sessionId]: false },
        lastError: null,
      }))

      return messages
    } catch (error) {
      set((state) => ({
        loadingSessionIds: { ...state.loadingSessionIds, [sessionId]: false },
        lastError: error instanceof Error ? error.message : '메시지 조회에 실패했습니다.',
      }))
      throw error
    }
  },
  sendMessage: async ({ sessionId, content }) => {
    const trimmedContent = content.trim()
    if (trimmedContent === '') {
      throw new Error('전송할 메시지를 입력해 주세요.')
    }

    const clientMessageId = createClientMessageId()
    const optimisticSessionId = sessionId ?? `pending_session_${clientMessageId}`
    const optimisticMessage: ChatMessageView = {
      id: `pending_message_${clientMessageId}`,
      sessionId: optimisticSessionId,
      role: 'user',
      content: trimmedContent,
      status: 'optimistic',
      clientMessageId,
      createdAt: new Date().toISOString(),
    }

    set((state) => ({
      messagesBySessionId: {
        ...state.messagesBySessionId,
        [optimisticSessionId]: [
          ...(state.messagesBySessionId[optimisticSessionId] ?? []),
          optimisticMessage,
        ],
      },
      pendingClientMessageIds: {
        ...state.pendingClientMessageIds,
        [clientMessageId]: optimisticSessionId,
      },
    }))

    const frame = await useAiRealtimeStore
      .getState()
      .sendCommand<AiRealtimeRawFrame>('session.message.create', {
        sessionId,
        content: trimmedContent,
        clientMessageId,
      })

    get().handleRealtimeFrame(frame)
    return frame
  },
  handleRealtimeFrame: (frame) => {
    switch (frame.type) {
      case 'session.list.result':
        mergeSessionList(frame, set)
        return
      case 'session.messages.list.result':
        mergeMessageList(frame, set)
        return
      case 'session.message.accepted':
        mergeAcceptedMessage(frame, set, get)
        return
      case 'session.message.delta':
        mergeAssistantDelta(frame, set)
        return
      case 'session.message.completed':
        mergeAssistantCompleted(frame, set)
        return
      default:
        return
    }
  },
  clearChatState: () =>
    set({
      sessionsById: {},
      messagesBySessionId: {},
      pendingClientMessageIds: {},
      loadingSessionIds: {},
      lastError: null,
    }),
}))

const getRawSessionList = (payload: SessionListResultPayload | unknown): RawAiSession[] => {
  if (!isJsonObject(payload)) {
    return []
  }

  const list = Array.isArray(payload.sessions)
    ? payload.sessions
    : Array.isArray(payload.items)
      ? payload.items
      : []

  return list.filter(isRawAiSession)
}

const getRawMessageList = (payload: SessionMessagesListResultPayload | unknown): RawAiMessage[] => {
  if (!isJsonObject(payload)) {
    return []
  }

  const list = Array.isArray(payload.messages)
    ? payload.messages
    : Array.isArray(payload.items)
      ? payload.items
      : []

  return list.filter(isRawAiMessage)
}

const toChatMessageView = (message: RawAiMessage): ChatMessageView => ({
  id: message.message_id,
  sessionId: message.session_id,
  role: message.role,
  content: message.content,
  status: message.role === 'assistant' ? 'completed' : 'accepted',
  taskRunId: typeof message.task_run_id === 'string' ? message.task_run_id : undefined,
  clientMessageId:
    typeof message.client_message_id === 'string' ? message.client_message_id : undefined,
  createdAt: typeof message.created_at === 'string' ? message.created_at : undefined,
  raw: message,
})

const mergeSessionList = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  const sessions = getRawSessionList(getFramePayload(frame))
  set((state) => ({
    sessionsById: {
      ...state.sessionsById,
      ...Object.fromEntries(sessions.map((session) => [session.session_id, session])),
    },
  }))
}

const mergeMessageList = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  const payload = getFramePayload(frame)
  const messages = getRawMessageList(payload).map(toChatMessageView)
  const sessionId = getStringField(payload, 'session_id', 'sessionId') ?? messages[0]?.sessionId

  if (sessionId === undefined) {
    return
  }

  set((state) => ({
    messagesBySessionId: { ...state.messagesBySessionId, [sessionId]: messages },
  }))
}

const mergeAcceptedMessage = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
  get: () => ChatState,
) => {
  const payload = getFramePayload(frame) as RawSessionMessageAcceptedPayload
  const sessionId = getStringField(payload, 'session_id', 'sessionId')
  const clientMessageId = getStringField(payload, 'client_message_id', 'clientMessageId')
  const userMessageId = getStringField(payload, 'user_message_id', 'userMessageId')
  const assistantMessageId = getStringField(payload, 'assistant_message_id', 'assistantMessageId')
  const taskRunId = getStringField(payload, 'task_run_id', 'taskRunId')

  if (sessionId === undefined) {
    return
  }

  const previousSessionId =
    clientMessageId !== undefined ? get().pendingClientMessageIds[clientMessageId] : undefined

  set((state) => {
    const sourceSessionId = previousSessionId ?? sessionId
    const previousMessages = state.messagesBySessionId[sourceSessionId] ?? []
    const acceptedMessages = previousMessages.map((message) => {
      if (message.clientMessageId !== clientMessageId) {
        return { ...message, sessionId }
      }
      return {
        ...message,
        id: userMessageId ?? message.id,
        sessionId,
        status: 'accepted' as const,
        taskRunId,
      }
    })

    const hasAssistantPlaceholder = acceptedMessages.some(
      (message) => message.id === assistantMessageId,
    )
    const assistantPlaceholder =
      assistantMessageId === undefined || hasAssistantPlaceholder
        ? []
        : [
            {
              id: assistantMessageId,
              sessionId,
              role: 'assistant',
              content: '',
              status: 'streaming' as const,
              taskRunId,
            },
          ]

    const pendingClientMessageIds = { ...state.pendingClientMessageIds }
    if (clientMessageId !== undefined) {
      delete pendingClientMessageIds[clientMessageId]
    }

    const messagesBySessionId = { ...state.messagesBySessionId }
    if (sourceSessionId !== sessionId) {
      delete messagesBySessionId[sourceSessionId]
    }
    messagesBySessionId[sessionId] = [...acceptedMessages, ...assistantPlaceholder]

    return { messagesBySessionId, pendingClientMessageIds }
  })
}

const mergeAssistantDelta = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  const payload = getFramePayload(frame) as RawSessionMessageDeltaPayload
  const sessionId = getStringField(payload, 'session_id', 'sessionId')
  const messageId = getStringField(payload, 'message_id', 'messageId')
  const delta =
    typeof payload.delta === 'string'
      ? payload.delta
      : typeof payload.content_delta === 'string'
        ? payload.content_delta
        : ''

  if (sessionId === undefined || messageId === undefined || delta === '') {
    return
  }

  set((state) => ({
    messagesBySessionId: {
      ...state.messagesBySessionId,
      [sessionId]: upsertAssistantMessage(state.messagesBySessionId[sessionId] ?? [], {
        id: messageId,
        sessionId,
        contentDelta: delta,
        status: 'streaming',
      }),
    },
  }))
}

const mergeAssistantCompleted = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  const payload = getFramePayload(frame) as RawSessionMessageCompletedPayload
  const sessionId = getStringField(payload, 'session_id', 'sessionId')
  const messageId = getStringField(payload, 'message_id', 'messageId')
  const content = typeof payload.content === 'string' ? payload.content : undefined

  if (sessionId === undefined || messageId === undefined) {
    return
  }

  set((state) => ({
    messagesBySessionId: {
      ...state.messagesBySessionId,
      [sessionId]: upsertAssistantMessage(state.messagesBySessionId[sessionId] ?? [], {
        id: messageId,
        sessionId,
        content,
        status: 'completed',
      }),
    },
  }))
}

const upsertAssistantMessage = (
  messages: ChatMessageView[],
  update: {
    id: string
    sessionId: string
    content?: string
    contentDelta?: string
    status: ChatMessageView['status']
  },
) => {
  const index = messages.findIndex((message) => message.id === update.id)
  if (index === -1) {
    return [
      ...messages,
      {
        id: update.id,
        sessionId: update.sessionId,
        role: 'assistant',
        content: update.content ?? update.contentDelta ?? '',
        status: update.status,
      },
    ]
  }

  return messages.map((message) =>
    message.id === update.id
      ? {
          ...message,
          content: update.content ?? `${message.content}${update.contentDelta ?? ''}`,
          status: update.status,
        }
      : message,
  )
}

const isRawAiSession = (value: unknown): value is RawAiSession =>
  isJsonObject(value) && typeof value.session_id === 'string'

const isRawAiMessage = (value: unknown): value is RawAiMessage =>
  isJsonObject(value) &&
  typeof value.message_id === 'string' &&
  typeof value.session_id === 'string' &&
  typeof value.role === 'string' &&
  typeof value.content === 'string'
