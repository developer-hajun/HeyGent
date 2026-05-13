import aiAxiosInstance from './aiAxiosInstance'

export type AgentSessionMessage = {
  id: number
  role: string
  content?: string | null
  toolName?: string | null
  toolCallId?: string | null
  toolCalls?: Array<Record<string, unknown>>
  metadata?: Record<string, unknown>
  timestamp?: string | number | null
  finishReason?: string | null
}

type AgentSessionMessagesResponse = {
  agentSessionId?: string
  items?: AgentSessionMessage[]
}

export async function listAgentSessionMessages(agentSessionId: string) {
  const { data } = await aiAxiosInstance.get<AgentSessionMessagesResponse>(
    `/agentSessions/${agentSessionId}/messages`,
    {
      params: { limit: 200 },
    },
  )
  return data.items ?? []
}
