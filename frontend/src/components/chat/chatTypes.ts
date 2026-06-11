import type { RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'

export type ChatConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'
  | 'auth-expired'

export type ChatMessageRole = 'user' | 'assistant'

export type ChatMessageStatus =
  | 'optimistic'
  | 'accepted'
  | 'streaming'
  | 'waiting'
  | 'completed'
  | 'failed'

export type ChatMessageView = {
  id: string
  role: ChatMessageRole
  content: string
  createdAt: string
  status: ChatMessageStatus
  taskRunId?: string
  clientMessageId?: string
}

export type SessionMessageAccepted = {
  sessionId: string
  userMessageId?: string
  assistantMessageId?: string
  taskRunId?: string
}

export type ActivityTone = 'idle' | 'running' | 'waiting' | 'completed' | 'failed'

export type ActivityItemView = {
  id: string
  title: string
  statusText: string
  tone: ActivityTone
  occurredAt?: string
}

export type SessionMessageCreateCallbacks = {
  onAccepted?: (accepted: SessionMessageAccepted) => void
  onDelta?: (delta: string) => void
  onCompleted?: (content: string) => void
  onTaskEvent?: (event: RawTaskEventPayload) => void
}
