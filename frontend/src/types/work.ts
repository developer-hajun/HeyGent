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
  title: string
  description: string
  rawUserInput: string
  executionInstruction: string
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

export interface WorkContextPreview {
  title: string
  labels: string[]
  commentsIncluded: number
  recentRunsIncluded: number
  promptPreview: string
}
