import type { ReactNode } from 'react'
import type { CommandUsageRecord, CommandUsageSummary } from '@/apis/aiCommandUsage'

export interface AgentRunUsageSummary {
  totalTokens: number
  estimatedCostUsd: number
}

interface UsageSummaryItem {
  label: string
  value: ReactNode
}

export function buildAgentRunUsageMap(records: CommandUsageRecord[]) {
  const usageByTaskRunId = new Map<string, AgentRunUsageSummary>()
  for (const record of records) {
    const taskRunId = record.taskRunId?.trim()
    if (!taskRunId) continue
    const current = usageByTaskRunId.get(taskRunId) ?? {
      totalTokens: 0,
      estimatedCostUsd: 0,
    }
    usageByTaskRunId.set(taskRunId, {
      totalTokens: current.totalTokens + (record.totalTokens ?? 0),
      estimatedCostUsd: current.estimatedCostUsd + (record.estimatedCostUsd ?? 0),
    })
  }
  return usageByTaskRunId
}

export function formatAgentRunTokenUsage(usage: AgentRunUsageSummary | undefined) {
  if (usage === undefined) return '-'
  return `${formatUsageNumber(usage.totalTokens)} tok`
}

export function formatAgentRunCostUsage(usage: AgentRunUsageSummary | undefined) {
  if (usage === undefined) return '-'
  return formatUsageCost(usage.estimatedCostUsd)
}

export function buildAgentUsageSummaryItems(
  summary: CommandUsageSummary | null,
  loading: boolean,
  error: string | null,
): UsageSummaryItem[] {
  if (loading && summary === null) {
    return [
      { label: '입력 토큰', value: '조회 중' },
      { label: '출력 토큰', value: '조회 중' },
      { label: '캐시 토큰', value: '조회 중' },
      { label: '예상 비용', value: '조회 중' },
    ]
  }

  if (error !== null && summary === null) {
    return [
      { label: '입력 토큰', value: '-' },
      { label: '출력 토큰', value: '-' },
      { label: '캐시 토큰', value: '-' },
      { label: '예상 비용', value: '-' },
    ]
  }

  return [
    { label: '입력 토큰', value: formatUsageNumber(summary?.inputTokens ?? 0) },
    { label: '출력 토큰', value: formatUsageNumber(summary?.outputTokens ?? 0) },
    { label: '캐시 토큰', value: formatUsageNumber(summary?.cachedInputTokens ?? 0) },
    { label: '예상 비용', value: formatUsageCost(summary?.estimatedCostUsd ?? 0) },
  ]
}

function formatUsageNumber(value: number) {
  return value.toLocaleString('ko-KR')
}

function formatUsageCost(value: number) {
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(2)}`
}
