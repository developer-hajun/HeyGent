import axiosInstance from './axiosInstance'

export interface CommandUsageParams {
  from?: string
  to?: string
  taskRunId?: string
  sessionId?: string
  limit?: number
}

export interface CommandUsageSummary {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  cachedInputTokens: number
  reasoningTokens: number
  estimatedCostUsd: number
  currency: string
  recordCount: number
}

export interface CommandUsageRecord {
  id: number
  userId: number
  providerName: string
  model: string
  taskRunId: string
  stepRunId?: string
  sessionId?: string
  requestId?: string
  inputTokens: number
  outputTokens: number
  totalTokens: number
  cachedInputTokens?: number
  reasoningTokens?: number
  estimatedCostUsd?: number
  currency: string
  metadata: Record<string, unknown>
  createdAt?: string
}

export interface CommandUsageData {
  summary: CommandUsageSummary
  records: CommandUsageRecord[]
}

export async function getCommandUsage(params: CommandUsageParams = {}): Promise<CommandUsageData> {
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: CommandUsageData
  }>('/api/v1/ai/usages/me/commands', { params })
  return data.data
}
