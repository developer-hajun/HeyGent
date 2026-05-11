import type { JsonObject, RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'

export type TaskRunAgentKind = 'main' | 'user_subagent' | 'worker' | 'domain' | string

export type TaskRunAgentRef = {
  id: string
  kind: TaskRunAgentKind
  profileId?: string | null
  profileKey?: string | null
  displayName: string
  agentSessionId?: string | null
  status?: string | null
  summary?: string | null
}

export type TaskRunDisplayContext = {
  sessionId?: string | null
  taskRunId: string
  stepRunId?: string | null
  assigneeAgent: TaskRunAgentRef
  actorAgent: TaskRunAgentRef
  delegatedAgents: TaskRunAgentRef[]
}

export type RawTaskRunStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'WAITING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | string

export type RawTaskRun = {
  task_run_id: string
  session_id?: string | null
  status?: RawTaskRunStatus | null
  title?: string | null
  goal?: string | null
  created_at?: string | null
  updated_at?: string | null
  completed_at?: string | null
  last_sequence?: number | null
  displayContext?: TaskRunDisplayContext | null
  [key: string]: unknown
}

export type RawStepRun = {
  step_run_id: string
  task_run_id: string
  title?: string | null
  goal?: string | null
  status?: RawTaskRunStatus | null
  step_order?: number | null
  stepOrder?: number | null
  internal_step_anchor?: boolean | null
  internalStepAnchor?: boolean | null
  sequence?: number | null
  started_at?: string | null
  completed_at?: string | null
  displayContext?: TaskRunDisplayContext | null
  [key: string]: unknown
}

export type RawApproval = {
  approval_id: string
  task_run_id: string
  step_run_id?: string | null
  status?: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | string
  title?: string | null
  description?: string | null
  payload?: JsonObject | null
  created_at?: string | null
  [key: string]: unknown
}

export type RawTaskRunSnapshot = {
  task?: RawTaskRun
  task_run?: RawTaskRun
  taskRun?: RawTaskRun
  steps?: RawStepRun[]
  step_runs?: RawStepRun[]
  stepRuns?: RawStepRun[]
  pending_approval?: RawApproval | null
  pendingApproval?: RawApproval | null
  approvals?: RawApproval[]
  events?: RawTaskEventPayload[]
  [key: string]: unknown
}

export type TaskRunStatusTone = 'idle' | 'running' | 'waiting' | 'completed' | 'failed'

export type ActivityItemView = {
  id: string
  taskRunId: string
  stepRunId?: string
  title: string
  statusText: string
  tone: TaskRunStatusTone
  sequence?: number
  occurredAt?: string
  displayContext?: TaskRunDisplayContext
  raw: RawTaskEventPayload
}

export type TaskRunSummaryView = {
  id: string
  title: string
  statusText: string
  tone: TaskRunStatusTone
  lastSequence?: number
  raw?: RawTaskRun
}

export type TaskRunDetailSummaryView = TaskRunSummaryView & {
  latestStepRun?: RawStepRun
  latestEvent?: RawTaskEventPayload
  pendingApproval?: RawApproval
  activityItems: ActivityItemView[]
  replayNeeded: boolean
  recovering: boolean
  recoveryAfterSequence?: number
}

export type TaskRunsActiveListResultPayload = {
  task_runs?: RawTaskRun[]
  taskRuns?: RawTaskRun[]
  items?: RawTaskRun[]
  [key: string]: unknown
}

export type TaskRunEventsReplayResultPayload = {
  task_run_id?: string
  taskRunId?: string
  events?: RawTaskEventPayload[]
  next_sequence?: number
  nextSequence?: number
  retention_exceeded?: boolean
  retentionExceeded?: boolean
  [key: string]: unknown
}
