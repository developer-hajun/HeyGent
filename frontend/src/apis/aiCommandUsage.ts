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
  const normalizedParams = withDefaultDateRange(params)
  const { data } = await axiosInstance.get<{
    status: number
    message: string
    data: CommandUsageData
  }>('/api/v1/ai/usages/me/commands', { params: normalizedParams })
  return data.data
}

function withDefaultDateRange(params: CommandUsageParams): CommandUsageParams {
  return {
    ...params,
    from: params.from ?? '1970-01-01',
    to: params.to ?? formatLocalDate(new Date()),
  }
}

function formatLocalDate(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
