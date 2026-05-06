import type { JsonObject } from '@/realtime/aiRealtimeTypes'

export type RawAiSession = {
  session_id: string
  title?: string | null
  archived_at?: string | null
  deleted_at?: string | null
  settings?: AiSessionSettings | JsonObject | null
  created_at?: string | null
  updated_at?: string | null
  last_message?: string | null
  last_message_at?: string | null
  last_task_run_status?: string | null
  active_task_run_id?: string | null
  [key: string]: unknown
}

export type AiSessionSettings = {
  model?: string | null
  provider?: string | null
  systemPrompt?: string | null
  toolsets?: string[] | null
  delegationPolicy?: JsonObject | null
  [key: string]: unknown
}

export type AiSessionSettingsPatch = Partial<AiSessionSettings>

export type AiModelOption = {
  id: string
  label: string
  provider?: string
  warning?: string | null
  isCurrent?: boolean
  raw?: JsonObject
}

export type AiModelProviderOption = {
  slug: string
  label?: string
  warning?: string | null
  isCurrent?: boolean
  models: AiModelOption[]
  raw?: JsonObject
}

export type ModelOptionsResultPayload = {
  model?: string | null
  providers?: AiModelProviderOption[]
  models?: AiModelOption[]
  [key: string]: unknown
}

export type RawAiMessageRole = 'user' | 'assistant' | 'system' | 'tool' | string

export type RawAiMessage = {
  message_id: string
  session_id: string
  role: RawAiMessageRole
  content: string
  created_at?: string | null
  task_run_id?: string | null
  client_message_id?: string | null
  metadata?: JsonObject | null
  [key: string]: unknown
}

export type ChatMessageStatus =
  | 'optimistic'
  | 'accepted'
  | 'streaming'
  | 'waiting'
  | 'completed'
  | 'failed'

export type ChatMessageView = {
  id: string
  sessionId: string
  role: RawAiMessageRole
  content: string
  status: ChatMessageStatus
  taskRunId?: string
  clientMessageId?: string
  createdAt?: string
  raw?: RawAiMessage
}

export type ChatSessionView = {
  id: string
  title: string
  lastMessage?: string
  lastMessageAt?: string
  activeTaskRunId?: string
  raw: RawAiSession
}

export type SessionListResultPayload = {
  sessions?: RawAiSession[]
  items?: RawAiSession[]
  cursor?: string | null
  next_cursor?: string | null
  [key: string]: unknown
}

export type SessionMessagesListResultPayload = {
  session_id?: string
  messages?: RawAiMessage[]
  items?: RawAiMessage[]
  cursor?: string | null
  next_cursor?: string | null
  [key: string]: unknown
}
