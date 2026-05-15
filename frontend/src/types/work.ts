export type WorkStatus =
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'in_review'
  | 'blocked'
  | 'done'
  | 'cancelled'

export interface WorkItem {
  workId: string
  identifier: string
  sessionId: string
  title: string
  description: string | null
  status: WorkStatus
  assigneeAgentId: string | null
  parentId: string | null
  flowOrder: number | null
  source: string
  rawUserInput: string | null
  executionInstruction: string | null
  expectedDeliverable: string | null
  acceptanceCriteria: string[]
  constraints: string[]
  metadata: Record<string, unknown>
  activeRunId: string | null
  latestRunId: string | null
  labelIds: string[]
  childCount: number
  completedChildCount: number
  blockedByCount: number
  recentRunIds: string[]
  commentCount: number
  blockedByWorkIds: string[]
  relatedWorkIds: string[]
  childWorkIds: string[]
  archivedAt: string | null
  createdAt: string | null
  updatedAt: string | null
  startedAt: string | null
  completedAt: string | null
  taskStatus?: string | null
}

export interface WorkListResponse {
  items: WorkItem[]
  totalCount: number
}

export interface CreateWorkRequest {
  clientRequestId: string
  title?: string | null
  description: string
  assigneeAgentId?: string | null
  rawUserInput: string
  executionInstruction: string
  startExecution?: boolean
  expectedDeliverable?: string | null
  acceptanceCriteria?: string[]
  constraints?: string[]
  labelNames?: string[]
  initialComment?: string | null
  metadata?: Record<string, unknown>
  flowOrder?: number | null
}

export interface WorkCreateResponse {
  work: WorkItem
  taskRunId: string | null
  taskStatus: string | null
}

export interface WorkComment {
  commentId: string
  workId: string
  authorType: string
  authorId: string | null
  taskRunId: string | null
  body: string
  resumeRequested: boolean
  metadata: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
}

export interface WorkRun {
  workId: string
  taskRunId: string
  runKind: string
  status: string
  createdAt: string | null
  updatedAt: string | null
}

export interface WorkWake {
  wakeId: string
  workId: string
  rootWorkId: string | null
  reason: string
  status: string
  requestedByTaskRunId: string | null
  taskRunId: string | null
  attempts: number
  lastError: string | null
  createdAt: string | null
  updatedAt: string | null
  claimedAt: string | null
  nextAttemptAt: string | null
  completedAt: string | null
}

export interface WorkRecoveryAction {
  actionId: string
  workId: string
  actionType: string
  status: string
  reason: string
  idempotencyKey: string
  taskRunId: string | null
  payload: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
  resolvedAt: string | null
}

export interface WorkLabel {
  labelId: string
  sessionId: string
  name: string
  color: string
  createdAt: string | null
  updatedAt: string | null
}

export interface WorkRelation {
  sourceWorkId: string
  targetWorkId: string
  relationType: 'blocks' | 'related'
  createdAt: string | null
}

export interface WorkFlowResponse {
  root: WorkItem
  items: WorkItem[]
  relations: WorkRelation[]
}

export interface WorkContextPreview {
  title: string
  labels: string[]
  commentsIncluded: number
  recentRunsIncluded: number
  promptPreview: string
}

export interface CreateChildWorkRequest {
  clientRequestId?: string | null
  title: string
  description?: string | null
  assigneeAgentId?: string | null
  acceptanceCriteria?: string[]
  blockParentUntilDone?: boolean
  flowOrder?: number | null
}

export interface UpdateWorkFlowOrderRequest {
  workIds: string[]
}

export interface WorkDocument {
  documentId: string
  workId: string
  documentKey: string
  title: string
  body: string
  format: string
  revisionNumber: number
  createdBy: string | null
  updatedBy: string | null
  createdAt: string | null
  updatedAt: string | null
}

export interface WorkDocumentRevision {
  revisionId: string
  documentId: string
  workId: string
  documentKey: string
  title: string
  body: string
  format: string
  revisionNumber: number
  createdBy: string | null
  createdAt: string | null
}

export interface WorkProduct {
  productId: string
  workId: string
  title: string
  summary: string | null
  productType: string
  status: string
  reviewState: string
  uri: string | null
  metadata: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
}

export type WorkInteractionKind = 'suggest_tasks' | 'ask_user_questions' | 'request_confirmation'
export type WorkInteractionStatus =
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'answered'
  | 'cancelled'
  | 'expired'
  | 'failed'

export interface WorkInteraction {
  interactionId: string
  workId: string
  kind: WorkInteractionKind
  status: WorkInteractionStatus
  title: string | null
  body: string | null
  payload: Record<string, unknown>
  response: Record<string, unknown>
  continuationPolicy: 'none' | 'wake_assignee' | 'wake_assignee_on_accept'
  createdAt: string | null
  updatedAt: string | null
}
