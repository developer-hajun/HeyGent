export interface AgentRunItemData {
  id: string
  status: string
  source?: string
  createdAt?: string
  sortTime?: number
  summary?: string
  tokens?: string
  cost?: string
  adapter?: string
  model?: string
  request?: string
  delegationInput?: string
  handoff?: string
  result?: string
  transcriptSessionId?: string
  parentTranscriptSessionId?: string
  agentName?: string
  timeline?: AgentRunTimelineItemData[]
}

export interface AgentRunTimelineItemData {
  id: string
  label: string
  message?: string
  status?: string
  time?: string
}
