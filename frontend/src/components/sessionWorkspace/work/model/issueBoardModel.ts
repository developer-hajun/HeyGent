export const ISSUE_BOARD_STATUSES = [
  'backlog',
  'todo',
  'in_progress',
  'in_review',
  'blocked',
  'done',
  'cancelled',
] as const
export const ISSUE_BOARD_LABELS = [
  { id: 'ui', name: 'UI', color: '#14b8a6' },
  { id: 'api', name: 'API', color: '#3b82f6' },
  { id: 'chat', name: '채팅', color: '#8b5cf6' },
  { id: 'execution', name: '실행', color: '#f97316' },
  { id: 'realtime', name: '실시간', color: '#06b6d4' },
  { id: 'taskrun', name: 'TaskRun', color: '#6366f1' },
  { id: 'board', name: '보드', color: '#10b981' },
  { id: 'assignee', name: '담당', color: '#f59e0b' },
  { id: 'copy', name: '문구', color: '#64748b' },
  { id: 'blocked', name: '차단', color: '#ef4444' },
] as const

export type IssueBoardStatus = (typeof ISSUE_BOARD_STATUSES)[number]
export interface IssueBoardLabel {
  id: string
  name: string
  color: string
}

export interface IssueBoardComment {
  id: string
  authorType: 'user' | 'agent' | 'system'
  authorName: string
  body: string
  createdAt: string
}

export interface IssueBoardRun {
  id: string
  status: 'queued' | 'running' | 'waiting' | 'completed' | 'failed'
  title: string
  summary: string
  startedAt: string
  finishedAt: string | null
}

export interface IssueBoardDocument {
  id: string
  title: string
  summary: string
  updatedAt: string
}

export interface IssueBoardRelatedItem {
  id: string
  identifier: string
  title: string
  status: IssueBoardStatus
}

export interface IssueBoardIssue {
  id: string
  identifier: string
  title: string
  description: string
  status: IssueBoardStatus
  assigneeAgentId: string | null
  parentId: string | null
  labels: string[]
  comments: IssueBoardComment[]
  runs: IssueBoardRun[]
  documents: IssueBoardDocument[]
  childItems: IssueBoardRelatedItem[]
  relatedItems: IssueBoardRelatedItem[]
  blockedBy: IssueBoardRelatedItem[]
  createdAt: string
  updatedAt: string
  startedAt: string | null
  completedAt: string | null
  live: boolean
}

export type IssueBoardColumnMap = Record<IssueBoardStatus, IssueBoardIssue[]>

export function createEmptyIssueBoardGroups(): IssueBoardColumnMap {
  const grouped = {} as IssueBoardColumnMap
  for (const status of ISSUE_BOARD_STATUSES) {
    grouped[status] = []
  }
  return grouped
}

export function groupIssuesByStatus(issues: IssueBoardIssue[]): IssueBoardColumnMap {
  const grouped = createEmptyIssueBoardGroups()
  for (const issue of issues) {
    grouped[issue.status].push(issue)
  }
  return grouped
}

export function moveIssueToStatus(
  issues: IssueBoardIssue[],
  issueId: string,
  status: IssueBoardStatus,
): IssueBoardIssue[] {
  const now = new Date().toISOString()
  return issues.map((issue) =>
    issue.id === issueId
      ? { ...issue, status, updatedAt: now, live: status === 'in_progress' }
      : issue,
  )
}

export function issueBoardStatusLabel(status: IssueBoardStatus) {
  const labels: Record<IssueBoardStatus, string> = {
    backlog: '보류',
    todo: '대기',
    in_progress: '진행 중',
    in_review: '검토 중',
    blocked: '차단됨',
    done: '완료',
    cancelled: '취소됨',
  }
  return labels[status]
}

export function createIssueBoardIdentifier(sequence: number) {
  return `TASK-${String(100 + sequence).padStart(3, '0')}`
}
