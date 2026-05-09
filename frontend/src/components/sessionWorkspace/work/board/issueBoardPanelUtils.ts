import type { WorkComment, WorkItem, WorkLabel } from '@/types/work'
import {
  ISSUE_BOARD_LABELS,
  ISSUE_BOARD_STATUSES,
  createIssueBoardFixtures,
  type IssueBoardIssue,
  type IssueBoardLabel,
  type IssueBoardStatus,
} from '../model/issueBoardModel'
import type { BoardAssignee, PersistedTodoBoardState, SortField } from './issueBoardPanelTypes'

export function toIssueBoardIssue(item: WorkItem, allItems: WorkItem[] = []): IssueBoardIssue {
  const now = new Date().toISOString()
  const createdAt = item.createdAt ?? now
  const updatedAt = item.updatedAt ?? createdAt

  return {
    id: item.workId,
    identifier: item.identifier,
    title: item.title,
    description: item.description ?? item.rawUserInput ?? '',
    status: item.status,
    assigneeAgentId: item.assigneeAgentId,
    labels: item.labelIds ?? [],
    comments: [],
    runs:
      item.latestRunId === null && item.activeRunId === null
        ? []
        : [
            {
              id: item.latestRunId ?? item.activeRunId ?? `${item.workId}:run`,
              status: toIssueBoardRunStatus(item),
              title: '실행',
              summary: item.taskStatus ?? item.status,
              startedAt: item.startedAt ?? createdAt,
              finishedAt: item.completedAt,
            },
          ],
    documents: [],
    relatedItems: (item.relatedWorkIds ?? [])
      .map((id) => toRelatedIssue(id, allItems))
      .filter(isRelatedIssue),
    blockedBy: (item.blockedByWorkIds ?? [])
      .map((id) => toRelatedIssue(id, allItems))
      .filter(isRelatedIssue),
    createdAt,
    updatedAt,
    startedAt: item.startedAt,
    completedAt: item.completedAt,
    live: item.activeRunId !== null || item.status === 'in_progress',
  }
}

export function toIssueBoardLabel(label: WorkLabel): IssueBoardLabel {
  return {
    id: label.labelId,
    name: label.name,
    color: label.color,
  }
}

export function toIssueBoardComment(comment: WorkComment): IssueBoardIssue['comments'][number] {
  return {
    id: comment.commentId,
    authorType: comment.authorType === 'system' ? 'system' : 'user',
    authorName: comment.authorType === 'system' ? '시스템' : '사용자',
    body: comment.body,
    createdAt: comment.createdAt ?? new Date().toISOString(),
  }
}

export function commentAuthorLabel(authorType: IssueBoardIssue['comments'][number]['authorType']) {
  const labels: Record<IssueBoardIssue['comments'][number]['authorType'], string> = {
    user: '사용자',
    agent: '에이전트',
    system: '시스템',
  }
  return labels[authorType]
}

export function runStatusLabel(status: IssueBoardIssue['runs'][number]['status']) {
  const labels: Record<IssueBoardIssue['runs'][number]['status'], string> = {
    queued: '대기',
    running: '실행 중',
    waiting: '대기 요청',
    completed: '완료',
    failed: '실패',
  }
  return labels[status]
}

export function resolveIssueLabels(labelIds: string[], labels: IssueBoardLabel[]) {
  const labelById = new Map(labels.map((label) => [label.id, label]))
  return labelIds
    .map((labelId) => labelById.get(labelId) ?? createFallbackLabel(labelId))
    .filter((label): label is IssueBoardLabel => Boolean(label))
}

export function createLabelIdentifier(name: string, labels: IssueBoardLabel[]) {
  const base =
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9가-힣]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'label'
  const existingIds = new Set(labels.map((label) => label.id))
  if (!existingIds.has(base)) return base
  let suffix = 2
  while (existingIds.has(`${base}-${suffix}`)) suffix += 1
  return `${base}-${suffix}`
}

export function isHexColor(value: string) {
  return /^#[0-9a-fA-F]{6}$/.test(value)
}

export function filterTodos(
  issues: IssueBoardIssue[],
  filters: {
    query: string
    statuses: IssueBoardStatus[]
    assignees: string[]
    labels: string[]
    liveOnly: boolean
  },
  assignees: BoardAssignee[],
  labels: IssueBoardLabel[],
) {
  const normalizedQuery = filters.query.trim().toLowerCase()
  return issues.filter((issue) => {
    if (filters.liveOnly && !issue.live) return false
    if (filters.statuses.length > 0 && !filters.statuses.includes(issue.status)) return false
    if (filters.assignees.length > 0) {
      if (!issue.assigneeAgentId) return filters.assignees.includes('__unassigned')
      if (!filters.assignees.includes(issue.assigneeAgentId)) return false
    }
    if (
      filters.labels.length > 0 &&
      !filters.labels.some((labelId) => issue.labels.includes(labelId))
    ) {
      return false
    }
    if (!normalizedQuery) return true
    const issueLabels = resolveIssueLabels(issue.labels, labels)
    return [
      issue.identifier,
      issue.title,
      issue.description,
      assigneeLabel(issue.assigneeAgentId, assignees),
      ...issueLabels.map((label) => label.name),
      ...issue.comments.map((comment) => comment.body),
      ...issue.runs.map((run) => `${run.title} ${run.summary}`),
    ].some((value) => value.toLowerCase().includes(normalizedQuery))
  })
}

export function sortTodos(issues: IssueBoardIssue[], sortField: SortField) {
  return [...issues].sort((left, right) => {
    if (sortField === 'title') return left.title.localeCompare(right.title)
    if (sortField === 'status') {
      return (
        ISSUE_BOARD_STATUSES.indexOf(left.status) - ISSUE_BOARD_STATUSES.indexOf(right.status) ||
        new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
      )
    }
    return new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
  })
}

export function nextSortField(sortField: SortField): SortField {
  if (sortField === 'updated') return 'status'
  if (sortField === 'status') return 'title'
  return 'updated'
}

export function sortFieldLabel(sortField: SortField) {
  const labels: Record<SortField, string> = {
    updated: '최근 수정',
    status: '상태순',
    title: '제목순',
  }
  return labels[sortField]
}

export function toggleValue<T>(values: T[], value: T) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

export function arraysEqual(left: readonly string[], right: readonly string[]) {
  if (left.length !== right.length) return false
  const leftSorted = [...left].sort()
  const rightSorted = [...right].sort()
  return leftSorted.every((value, index) => value === rightSorted[index])
}

export function loadTodoBoardState(storageKey: string, sessionId: string): PersistedTodoBoardState {
  const fallback: PersistedTodoBoardState = {
    issues: createIssueBoardFixtures(sessionId),
    labels: [...ISSUE_BOARD_LABELS],
    query: '',
    viewMode: 'list',
    sortField: 'updated',
    selectedStatuses: [],
    selectedAssignees: [],
    selectedLabels: [],
    liveOnly: false,
  }

  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (raw === null) return fallback
    const parsed = JSON.parse(raw) as Partial<PersistedTodoBoardState>
    return {
      issues: normalizeIssues(parsed.issues, fallback.issues),
      labels: normalizeLabels(parsed.labels, fallback.labels),
      query: typeof parsed.query === 'string' ? parsed.query : fallback.query,
      viewMode:
        parsed.viewMode === 'list' || parsed.viewMode === 'board'
          ? parsed.viewMode
          : fallback.viewMode,
      sortField: normalizeSortField(parsed.sortField, fallback.sortField),
      selectedStatuses: normalizeStatuses(parsed.selectedStatuses),
      selectedAssignees: normalizeAssignees(parsed.selectedAssignees),
      selectedLabels: normalizeStringArray(parsed.selectedLabels),
      liveOnly: parsed.liveOnly === true,
    }
  } catch {
    return fallback
  }
}

export function saveTodoBoardState(storageKey: string, state: PersistedTodoBoardState) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(state))
  } catch {
    return
  }
}

export function assigneeLabel(value: string | null, assignees: BoardAssignee[]) {
  if (value === null) return '담당자 없음'
  return assignees.find((assignee) => assignee.id === value)?.name ?? value
}

export function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return '알 수 없음'
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60_000))
  if (diffMinutes < 1) return '방금 전'
  if (diffMinutes < 60) return `${diffMinutes}분 전`
  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}시간 전`
  return `${Math.round(diffHours / 24)}일 전`
}

function toRelatedIssue(
  workId: string,
  allItems: WorkItem[],
): IssueBoardIssue['relatedItems'][number] | null {
  const item = allItems.find((candidate) => candidate.workId === workId)
  if (!item) return null
  return {
    id: item.workId,
    identifier: item.identifier,
    title: item.title,
    status: item.status,
  }
}

function isRelatedIssue(
  item: IssueBoardIssue['relatedItems'][number] | null,
): item is IssueBoardIssue['relatedItems'][number] {
  return item !== null
}

function toIssueBoardRunStatus(item: WorkItem): IssueBoardIssue['runs'][number]['status'] {
  if (item.activeRunId !== null) return 'running'
  if (item.status === 'done') return 'completed'
  if (item.status === 'blocked') return 'waiting'
  if (item.status === 'cancelled') return 'failed'
  return 'queued'
}

function createFallbackLabel(labelId: string): IssueBoardLabel {
  return {
    id: labelId,
    name: labelId,
    color: '#64748b',
  }
}

function normalizeIssues(value: unknown, fallback: IssueBoardIssue[]) {
  if (!Array.isArray(value)) return fallback
  const issues = value.filter((item): item is IssueBoardIssue => isIssueBoardIssue(item))
  return issues.length > 0 ? issues : fallback
}

function normalizeLabels(value: unknown, fallback: IssueBoardLabel[]) {
  if (!Array.isArray(value)) return fallback
  const labels = value.filter((item): item is IssueBoardLabel => isIssueBoardLabel(item))
  return labels.length > 0 ? labels : fallback
}

function isIssueBoardLabel(value: unknown): value is IssueBoardLabel {
  if (typeof value !== 'object' || value === null) return false
  const label = value as Record<string, unknown>
  return (
    typeof label.id === 'string' &&
    typeof label.name === 'string' &&
    typeof label.color === 'string' &&
    isHexColor(label.color)
  )
}

function isIssueBoardIssue(value: unknown): value is IssueBoardIssue {
  if (typeof value !== 'object' || value === null) return false
  const issue = value as Record<string, unknown>
  return (
    typeof issue.id === 'string' &&
    typeof issue.identifier === 'string' &&
    typeof issue.title === 'string' &&
    typeof issue.description === 'string' &&
    isIssueBoardStatus(issue.status) &&
    isKnownAssigneeId(issue.assigneeAgentId) &&
    Array.isArray(issue.labels) &&
    issue.labels.every((label) => typeof label === 'string') &&
    Array.isArray(issue.comments) &&
    issue.comments.every(isIssueBoardComment) &&
    Array.isArray(issue.runs) &&
    issue.runs.every(isIssueBoardRun) &&
    Array.isArray(issue.documents) &&
    issue.documents.every(isIssueBoardDocument) &&
    Array.isArray(issue.relatedItems) &&
    issue.relatedItems.every(isIssueBoardRelatedItem) &&
    Array.isArray(issue.blockedBy) &&
    issue.blockedBy.every(isIssueBoardRelatedItem) &&
    typeof issue.createdAt === 'string' &&
    typeof issue.updatedAt === 'string' &&
    (issue.startedAt === null || typeof issue.startedAt === 'string') &&
    (issue.completedAt === null || typeof issue.completedAt === 'string') &&
    typeof issue.live === 'boolean'
  )
}

function isIssueBoardComment(value: unknown): value is IssueBoardIssue['comments'][number] {
  if (typeof value !== 'object' || value === null) return false
  const comment = value as Record<string, unknown>
  return (
    typeof comment.id === 'string' &&
    (comment.authorType === 'user' ||
      comment.authorType === 'agent' ||
      comment.authorType === 'system') &&
    typeof comment.authorName === 'string' &&
    typeof comment.body === 'string' &&
    typeof comment.createdAt === 'string'
  )
}

function isIssueBoardRun(value: unknown): value is IssueBoardIssue['runs'][number] {
  if (typeof value !== 'object' || value === null) return false
  const run = value as Record<string, unknown>
  return (
    typeof run.id === 'string' &&
    (run.status === 'queued' ||
      run.status === 'running' ||
      run.status === 'waiting' ||
      run.status === 'completed' ||
      run.status === 'failed') &&
    typeof run.title === 'string' &&
    typeof run.summary === 'string' &&
    typeof run.startedAt === 'string' &&
    (run.finishedAt === null || typeof run.finishedAt === 'string')
  )
}

function isIssueBoardDocument(value: unknown): value is IssueBoardIssue['documents'][number] {
  if (typeof value !== 'object' || value === null) return false
  const document = value as Record<string, unknown>
  return (
    typeof document.id === 'string' &&
    typeof document.title === 'string' &&
    typeof document.summary === 'string' &&
    typeof document.updatedAt === 'string'
  )
}

function isIssueBoardRelatedItem(value: unknown): value is IssueBoardIssue['relatedItems'][number] {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return (
    typeof item.id === 'string' &&
    typeof item.identifier === 'string' &&
    typeof item.title === 'string' &&
    isIssueBoardStatus(item.status)
  )
}

function normalizeAssignees(value: unknown): string[] {
  return normalizeStringArray(value)
}

function normalizeSortField(value: unknown, fallback: SortField): SortField {
  return value === 'updated' || value === 'status' || value === 'title' ? value : fallback
}

function normalizeStatuses(value: unknown): IssueBoardStatus[] {
  return normalizeStringArray(value).filter((item): item is IssueBoardStatus =>
    isIssueBoardStatus(item),
  )
}

function normalizeStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function isIssueBoardStatus(value: unknown): value is IssueBoardStatus {
  return typeof value === 'string' && ISSUE_BOARD_STATUSES.includes(value as IssueBoardStatus)
}

function isKnownAssigneeId(value: unknown): value is IssueBoardIssue['assigneeAgentId'] {
  if (value === null) return true
  return typeof value === 'string'
}
