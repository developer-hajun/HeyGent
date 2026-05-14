import type { JsonObject, RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'

export type TaskRunAgentKind = 'main' | 'user_subagent' | 'worker' | 'domain'

export type TaskRunStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'WAITING'
  | 'BLOCKED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELED'

export type TaskRunSource = 'active' | 'recent'

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELED'

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

export type RawTaskRunStatus = TaskRunStatus | 'CANCELLED' | string

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
  status?: ApprovalStatus | 'CANCELLED' | string
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
  task_runs?: RawActiveTaskRun[]
  taskRuns?: RawActiveTaskRun[]
  items?: RawActiveTaskRun[]
  total_count?: number
  totalCount?: number
  [key: string]: unknown
}

export type RawActiveTaskRun = RawTaskRun & {
  source?: TaskRunSource
  current_step_run_id?: string | null
  currentStepRunId?: string | null
  current_step?: RawStepRun | null
  currentStep?: RawStepRun | null
  wait_reason?: string | null
  waitReason?: string | null
  pending_approval?: RawApproval | null
  pendingApproval?: RawApproval | null
}

export type TaskRunEventsReplayResultPayload = {
  task_run_id?: string
  taskRunId?: string
  events?: RawTaskEventPayload[]
  latest_sequence?: number
  latestSequence?: number
  next_sequence?: number
  nextSequence?: number
  retention_exceeded?: boolean
  retentionExceeded?: boolean
  [key: string]: unknown
}

export type TaskRunFlowActivity = {
  event_type?: string
  eventType?: string
  status?: RawTaskRunStatus | null
  summary_message?: string | null
  summaryMessage?: string | null
  occurred_at?: string | null
  occurredAt?: string | null
}

export type TaskRunFlowWorkerSession = {
  session_id?: string
  sessionId?: string
  status?: string | null
  summary?: string | null
  agent_id?: string | null
  agentId?: string | null
  profile_key?: string | null
  profileKey?: string | null
}

export type TaskRunFlowNode = {
  step_run_id?: string
  stepRunId?: string
  step_order?: number
  stepOrder?: number
  title?: string | null
  status?: RawTaskRunStatus | null
  step_type?: string
  stepType?: string
  worker_session_id?: string | null
  workerSessionId?: string | null
  worker_session?: TaskRunFlowWorkerSession | null
  workerSession?: TaskRunFlowWorkerSession | null
  activity?: TaskRunFlowActivity[]
  [key: string]: unknown
}

export type TaskRunFlowEdge = {
  from_step_run_id?: string | null
  fromStepRunId?: string | null
  to_step_run_id?: string | null
  toStepRunId?: string | null
  to_task_run_id?: string | null
  toTaskRunId?: string | null
  to_agent_session_id?: string | null
  toAgentSessionId?: string | null
  relation?: string
  [key: string]: unknown
}

export type TaskRunFlowResponse = {
  task_run_id?: string
  taskRunId?: string
  status?: RawTaskRunStatus | null
  title?: string | null
  current_step_run_id?: string | null
  currentStepRunId?: string | null
  summary?: string | null
  nodes?: TaskRunFlowNode[]
  edges?: TaskRunFlowEdge[]
  [key: string]: unknown
}
