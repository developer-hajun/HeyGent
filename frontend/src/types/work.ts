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

export interface WorkContextPreview {
  title: string
  labels: string[]
  commentsIncluded: number
  recentRunsIncluded: number
  promptPreview: string
}
