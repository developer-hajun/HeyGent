import type { CommandUsageRecord } from '@/apis/aiCommandUsage'
import type { AgentProfile } from '@/apis/agents'
import type { RawTaskRun } from '@/types/taskRuns'

const usageRecordsBySessionId = new Map<string, CommandUsageRecord[]>()
const taskRunsBySessionId = new Map<string, RawTaskRun[]>()
const mainAgentProfileBySessionId = new Map<string, AgentProfile>()

export function getCachedUsageRecords(sessionId: string) {
  return usageRecordsBySessionId.get(sessionId)
}

export function setCachedUsageRecords(sessionId: string, records: CommandUsageRecord[]) {
  usageRecordsBySessionId.set(sessionId, records)
}

export function getCachedTaskRuns(sessionId: string) {
  return taskRunsBySessionId.get(sessionId)
}

export function setCachedTaskRuns(sessionId: string, taskRuns: RawTaskRun[]) {
  taskRunsBySessionId.set(sessionId, taskRuns)
}

export function getCachedMainAgentProfile(sessionId: string) {
  return mainAgentProfileBySessionId.get(sessionId) ?? null
}

export function setCachedMainAgentProfile(sessionId: string, profile: AgentProfile) {
  mainAgentProfileBySessionId.set(sessionId, profile)
}
