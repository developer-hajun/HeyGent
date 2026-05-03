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
  ChatMessageStatus,
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
    // 서버 accepted가 오기 전에도 사용자가 보낸 문장을 즉시 보여 주기 위한 임시 메시지다.
    // accepted를 받으면 서버/DB message id와 실제 session id로 치환한다.
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

    try {
      const frame = await useAiRealtimeStore
        .getState()
        .sendCommand<AiRealtimeRawFrame>('session.message.create', {
          sessionId,
          content: trimmedContent,
          clientMessageId,
        })

      get().handleRealtimeFrame(frame)
      return frame
    } catch (error) {
      markOptimisticMessageFailed(clientMessageId, set)
      throw error
    }
  },
  handleRealtimeFrame: (frame) => {
    switch (frame.type) {
      case 'session.list.result':
        mergeSessionList(frame, set)
        return
      case 'session.messages.list.result':
      case 'session.messages.result':
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

  return list.map(normalizeRawAiMessage).filter((message) => message !== null)
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

const upsertSessionPreview = (
  state: ChatState,
  input: {
    sessionId: string
    title?: string
    lastMessage?: string
    activeTaskRunId?: string | null
    lastTaskRunStatus?: string
  },
) => {
  const previous = state.sessionsById[input.sessionId]
  const now = new Date().toISOString()
  const hasActiveTaskRunId = Object.prototype.hasOwnProperty.call(input, 'activeTaskRunId')

  return {
    ...state.sessionsById,
    [input.sessionId]: {
      ...(previous ?? {
        session_id: input.sessionId,
        status: 'ACTIVE',
        source: 'api.session',
        created_at: now,
      }),
      title: previous?.title ?? input.title,
      last_message: input.lastMessage ?? previous?.last_message,
      last_message_at: now,
      active_task_run_id: hasActiveTaskRunId ? input.activeTaskRunId : previous?.active_task_run_id,
      last_task_run_status: input.lastTaskRunStatus ?? previous?.last_task_run_status,
      updated_at: now,
      message_count:
        typeof previous?.message_count === 'number' ? previous.message_count : undefined,
    },
  }
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
      (message) =>
        (assistantMessageId !== undefined && message.id === assistantMessageId) ||
        (taskRunId !== undefined &&
          message.role === 'assistant' &&
          message.taskRunId === taskRunId),
    )
    const placeholderId =
      assistantMessageId ?? (taskRunId === undefined ? undefined : `assistant_${taskRunId}`)
    // accepted는 "작업을 시작했다"는 응답이고 자연어 답변은 뒤이어 온다.
    // 그래서 completed/delta가 오기 전까지 빈 assistant placeholder를 만들어 진행 중 상태를 보여 준다.
    const assistantPlaceholder =
      placeholderId === undefined || hasAssistantPlaceholder
        ? []
        : [
            {
              id: placeholderId,
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

    return {
      messagesBySessionId,
      pendingClientMessageIds,
      sessionsById: upsertSessionPreview(state, {
        sessionId,
        title: acceptedMessages[0]?.content,
        lastMessage:
          acceptedMessages.find((message) => message.clientMessageId === clientMessageId)
            ?.content ?? acceptedMessages.find((message) => message.role === 'user')?.content,
        activeTaskRunId: taskRunId,
        lastTaskRunStatus: 'RUNNING',
      }),
    }
  })
}

const mergeAssistantDelta = (
  frame: AiRealtimeRawFrame,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  const payload = getFramePayload(frame) as RawSessionMessageDeltaPayload
  const sessionId = getStringField(payload, 'session_id', 'sessionId')
  const messageId = getStringField(payload, 'message_id', 'messageId')
  const taskRunId = getStringField(payload, 'task_run_id', 'taskRunId')
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
        taskRunId,
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
  const taskRunId = getStringField(payload, 'task_run_id', 'taskRunId')
  const content = typeof payload.content === 'string' ? payload.content : undefined
  const status = getStringField(payload, 'status')
  const shouldClearRunningState = isTerminalSessionMessageCompletion(status, taskRunId)

  if (sessionId === undefined || messageId === undefined) {
    return
  }

  set((state) => {
    const nextMessages = upsertAssistantMessage(state.messagesBySessionId[sessionId] ?? [], {
      id: messageId,
      sessionId,
      content,
      status: 'completed',
      taskRunId,
    })

    return {
      messagesBySessionId: {
        ...state.messagesBySessionId,
        [sessionId]: nextMessages,
      },
      sessionsById: upsertSessionPreview(state, {
        sessionId,
        lastMessage: content,
        activeTaskRunId: shouldClearRunningState ? null : taskRunId,
        lastTaskRunStatus: status,
      }),
    }
  })
}

const isTerminalSessionMessageCompletion = (status: string | undefined, taskRunId?: string) => {
  if (
    status === 'COMPLETED' ||
    status === 'FAILED' ||
    status === 'CANCELED' ||
    status === 'CANCELLED'
  ) {
    return true
  }

  return status === undefined && taskRunId !== undefined
}

const markOptimisticMessageFailed = (
  clientMessageId: string,
  set: (partial: Partial<ChatState> | ((state: ChatState) => Partial<ChatState>)) => void,
) => {
  set((state) => {
    const pendingSessionId = state.pendingClientMessageIds[clientMessageId]
    if (pendingSessionId === undefined) {
      return { pendingClientMessageIds: state.pendingClientMessageIds }
    }

    const pendingClientMessageIds = { ...state.pendingClientMessageIds }
    delete pendingClientMessageIds[clientMessageId]

    return {
      pendingClientMessageIds,
      messagesBySessionId: {
        ...state.messagesBySessionId,
        [pendingSessionId]: updateMessageStatus(
          state.messagesBySessionId[pendingSessionId] ?? [],
          clientMessageId,
          'failed',
        ),
      },
    }
  })
}

const updateMessageStatus = (
  messages: ChatMessageView[],
  clientMessageId: string,
  status: ChatMessageStatus,
) =>
  messages.map((message) =>
    message.clientMessageId === clientMessageId ? { ...message, status } : message,
  )

const upsertAssistantMessage = (
  messages: ChatMessageView[],
  update: {
    id: string
    sessionId: string
    content?: string
    contentDelta?: string
    taskRunId?: string
    status: ChatMessageView['status']
  },
) => {
  const index = messages.findIndex(
    (message) =>
      message.id === update.id ||
      (update.taskRunId !== undefined &&
        message.role === 'assistant' &&
        message.taskRunId === update.taskRunId &&
        message.status === 'streaming'),
  )
  if (index === -1) {
    return [
      ...messages,
      {
        id: update.id,
        sessionId: update.sessionId,
        role: 'assistant',
        content: update.content ?? update.contentDelta ?? '',
        status: update.status,
        taskRunId: update.taskRunId,
      },
    ]
  }

  return messages.map((message, messageIndex) =>
    messageIndex === index
      ? {
          ...message,
          id: update.id,
          content: update.content ?? `${message.content}${update.contentDelta ?? ''}`,
          status: update.status,
          taskRunId: update.taskRunId ?? message.taskRunId,
        }
      : message,
  )
}

const isRawAiSession = (value: unknown): value is RawAiSession =>
  isJsonObject(value) && typeof value.session_id === 'string'

const normalizeRawAiMessage = (value: unknown): RawAiMessage | null => {
  if (!isJsonObject(value)) {
    return null
  }

  const messageId = getStringField(value, 'message_id', 'messageId') ?? getStringField(value, 'id')
  const sessionId = getStringField(value, 'session_id', 'sessionId')
  const role = getStringField(value, 'role')
  const content =
    typeof value.content === 'string'
      ? value.content
      : typeof value.text === 'string'
        ? value.text
        : undefined

  if (
    messageId === undefined ||
    sessionId === undefined ||
    role === undefined ||
    content === undefined
  ) {
    return null
  }

  return {
    ...value,
    message_id: messageId,
    session_id: sessionId,
    role,
    content,
    task_run_id:
      getStringField(value, 'task_run_id', 'taskRunId') ??
      (typeof value.task_run_id === 'string' ? value.task_run_id : undefined),
    client_message_id:
      getStringField(value, 'client_message_id', 'clientMessageId') ??
      (typeof value.client_message_id === 'string' ? value.client_message_id : undefined),
  }
}
