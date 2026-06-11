import type { ReactNode } from 'react'
import type { CommandUsageRecord, CommandUsageSummary } from '@/apis/aiCommandUsage'
import type { AgentUsageRowData } from '@/components/sessionWorkspace/AgentDetailPanels'

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

export function buildUsageSummaryFromRecords(records: CommandUsageRecord[]): CommandUsageSummary {
  return records.reduce<CommandUsageSummary>(
    (summary, record) => ({
      inputTokens: summary.inputTokens + (record.inputTokens ?? 0),
      outputTokens: summary.outputTokens + (record.outputTokens ?? 0),
      totalTokens: summary.totalTokens + (record.totalTokens ?? 0),
      cachedInputTokens: summary.cachedInputTokens + (record.cachedInputTokens ?? 0),
      reasoningTokens: summary.reasoningTokens + (record.reasoningTokens ?? 0),
      estimatedCostUsd: summary.estimatedCostUsd + (record.estimatedCostUsd ?? 0),
      currency: record.currency ?? summary.currency,
      recordCount: summary.recordCount + 1,
    }),
    {
      inputTokens: 0,
      outputTokens: 0,
      totalTokens: 0,
      cachedInputTokens: 0,
      reasoningTokens: 0,
      estimatedCostUsd: 0,
      currency: 'USD',
      recordCount: 0,
    },
  )
}

export function filterUsageRecordsByTaskRunIds(
  records: CommandUsageRecord[],
  taskRunIds: Iterable<string>,
) {
  const allowed = new Set([...taskRunIds].map((id) => id.trim()).filter(Boolean))
  return records.filter((record) => allowed.has(record.taskRunId?.trim() ?? ''))
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

export function buildAgentUsageRows(records: CommandUsageRecord[]): AgentUsageRowData[] {
  return [...records]
    .filter(
      (record) =>
        (record.totalTokens ?? 0) > 0 ||
        (record.inputTokens ?? 0) > 0 ||
        (record.outputTokens ?? 0) > 0 ||
        (record.estimatedCostUsd ?? 0) > 0,
    )
    .sort((first, second) => getRecordTime(second) - getRecordTime(first))
    .map((record) => ({
      cost: formatUsageCost(record.estimatedCostUsd ?? 0),
      date: formatUsageDate(record.createdAt),
      input: formatUsageNumber(record.inputTokens ?? 0),
      output: formatUsageNumber(record.outputTokens ?? 0),
      run: record.taskRunId ? record.taskRunId.slice(0, 8) : '-',
    }))
}

function formatUsageNumber(value: number) {
  return value.toLocaleString('ko-KR')
}

function formatUsageCost(value: number) {
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(2)}`
}

function getRecordTime(record: CommandUsageRecord) {
  if (!record.createdAt) return 0
  return parseServerTimestamp(record.createdAt) ?? 0
}

function formatUsageDate(value?: string) {
  if (!value) return '-'
  const time = parseServerTimestamp(value)
  if (time === null) return '-'
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(time))
}

/**
 * 서버에서 내려온 시각 문자열을 안정적으로 파싱한다.
 * timezone 정보(`Z`, `+09:00` 등)가 없으면 UTC로 가정 — 백엔드가 LocalDateTime을
 * 그대로 직렬화하는 경우 브라우저가 로컬 타임으로 오해석하지 않도록 보정.
 */
export function parseServerTimestamp(value: string): number | null {
  const hasTimezone = /(Z|[+-]\d{2}:?\d{2})$/.test(value)
  const normalized = hasTimezone ? value : `${value}Z`
  const time = new Date(normalized).getTime()
  return Number.isFinite(time) ? time : null
}
