import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUpDown,
  ArrowUp,
  Bot,
  Check,
  ChevronDown,
  Circle,
  CircleCheck,
  Clock3,
  Columns3,
  FileText,
  Filter,
  FolderKanban,
  List,
  ListTree,
  MessageSquare,
  Minus,
  PauseCircle,
  PlayCircle,
  Plus,
  Search,
  Send,
  SlidersHorizontal,
  Tag,
  UserRound,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/components/ui/utils'
import { useSessionStore } from '@/store/useSessionStore'
import {
  ISSUE_BOARD_LABELS,
  ISSUE_BOARD_PRIORITIES,
  ISSUE_BOARD_STATUSES,
  createIssueBoardIdentifier,
  createIssueBoardFixtures,
  groupIssuesByStatus,
  issueBoardPriorityLabel,
  issueBoardStatusLabel,
  moveIssueToStatus,
  type IssueBoardIssue,
  type IssueBoardLabel,
  type IssueBoardPriority,
  type IssueBoardStatus,
} from './issueBoardModel'

const MAIN_AGENT_ASSIGNEE = { id: 'main-agent', name: '메인 에이전트', icon: UserRound } as const

const QUICK_FILTERS = [
  { id: 'all', label: '전체', statuses: [] },
  { id: 'active', label: '진행 항목', statuses: ['todo', 'in_progress', 'blocked'] },
  { id: 'blocked', label: '차단됨', statuses: ['blocked'] },
  { id: 'done', label: '완료', statuses: ['done'] },
] as const

type ViewMode = 'list' | 'board'
type SortField = 'updated' | 'title' | 'status'
type DetailTab = 'chat' | 'runs' | 'activity' | 'related'
type BoardAssignee = {
  id: string
  name: string
  icon: typeof UserRound
}

interface PersistedTodoBoardState {
  issues: IssueBoardIssue[]
  labels: IssueBoardLabel[]
  query: string
  viewMode: ViewMode
  sortField: SortField
  selectedStatuses: IssueBoardStatus[]
  selectedAssignees: string[]
  selectedLabels: string[]
  liveOnly: boolean
}

export function IssueBoardPanel({ sessionId }: { sessionId: string }) {
  const storageKey = `heygent-task-board:v4:${sessionId}`
  const agentPanelsBySessionId = useSessionStore((state) => state.agentPanelsBySessionId)
  const assignees = useMemo<BoardAssignee[]>(() => {
    const agentPanels = agentPanelsBySessionId[sessionId] ?? []
    return [
      MAIN_AGENT_ASSIGNEE,
      ...agentPanels.map((panel) => ({
        id: panel.id,
        name: panel.agent.name,
        icon: Bot,
      })),
    ]
  }, [agentPanelsBySessionId, sessionId])
  const [initialState] = useState(() => loadTodoBoardState(storageKey, sessionId))
  const [issues, setIssues] = useState(initialState.issues)
  const [labels, setLabels] = useState<IssueBoardLabel[]>(initialState.labels)
  const [query, setQuery] = useState(initialState.query)
  const [viewMode, setViewMode] = useState<ViewMode>(initialState.viewMode)
  const [sortField, setSortField] = useState<SortField>(initialState.sortField)
  const [selectedStatuses, setSelectedStatuses] = useState<IssueBoardStatus[]>(
    initialState.selectedStatuses,
  )
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>(
    initialState.selectedAssignees,
  )
  const [selectedLabels, setSelectedLabels] = useState<string[]>(initialState.selectedLabels)
  const [liveOnly, setLiveOnly] = useState(initialState.liveOnly)
  const [draggedIssueId, setDraggedIssueId] = useState<string | null>(null)
  const [dragOverStatus, setDragOverStatus] = useState<IssueBoardStatus | null>(null)
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null)

  useEffect(() => {
    saveTodoBoardState(storageKey, {
      issues,
      labels,
      query,
      viewMode,
      sortField,
      selectedStatuses,
      selectedAssignees,
      selectedLabels,
      liveOnly,
    })
  }, [
    issues,
    labels,
    liveOnly,
    query,
    selectedAssignees,
    selectedLabels,
    selectedStatuses,
    sortField,
    storageKey,
    viewMode,
  ])

  const filteredIssues = useMemo(
    () =>
      sortTodos(
        filterTodos(
          issues,
          {
            query,
            statuses: selectedStatuses,
            assignees: selectedAssignees,
            labels: selectedLabels,
            liveOnly,
          },
          assignees,
          labels,
        ),
        sortField,
      ),
    [
      assignees,
      issues,
      labels,
      liveOnly,
      query,
      selectedAssignees,
      selectedLabels,
      selectedStatuses,
      sortField,
    ],
  )
  const grouped = useMemo(() => groupIssuesByStatus(filteredIssues), [filteredIssues])
  const selectedIssue = selectedIssueId
    ? (issues.find((issue) => issue.id === selectedIssueId) ?? null)
    : null
  const activeFilterCount =
    Number(selectedStatuses.length > 0) +
    Number(selectedAssignees.length > 0) +
    Number(selectedLabels.length > 0) +
    Number(liveOnly)

  const moveIssue = (issueId: string, status: IssueBoardStatus) => {
    setIssues((current) => moveIssueToStatus(current, issueId, status))
  }

  const assignIssue = (issueId: string, assigneeAgentId: string | null) => {
    const now = new Date().toISOString()
    setIssues((current) =>
      current.map((issue) =>
        issue.id === issueId ? { ...issue, assigneeAgentId, updatedAt: now } : issue,
      ),
    )
  }

  const updateIssue = (issueId: string, patch: Partial<IssueBoardIssue>) => {
    const now = new Date().toISOString()
    setIssues((current) =>
      current.map((issue) =>
        issue.id === issueId
          ? {
              ...issue,
              ...patch,
              id: issue.id,
              identifier: issue.identifier,
              updatedAt: now,
            }
          : issue,
      ),
    )
  }

  const addIssueComment = (issueId: string, body: string) => {
    const trimmed = body.trim()
    if (!trimmed) return
    const now = new Date().toISOString()
    setIssues((current) =>
      current.map((issue) =>
        issue.id === issueId
          ? {
              ...issue,
              comments: [
                ...issue.comments,
                {
                  id: `${issue.id}:comment:${Date.now()}`,
                  authorType: 'user',
                  authorName: '사용자',
                  body: trimmed,
                  createdAt: now,
                },
              ],
              updatedAt: now,
            }
          : issue,
      ),
    )
  }

  const createLabel = (label: IssueBoardLabel) => {
    setLabels((current) => {
      if (current.some((item) => item.id === label.id)) return current
      return [...current, label]
    })
  }

  const resetFilters = () => {
    setQuery('')
    setSelectedStatuses([])
    setSelectedAssignees([])
    setSelectedLabels([])
    setLiveOnly(false)
  }

  const createNewTodo = () => {
    const now = new Date().toISOString()
    const sequence = issues.length + 1
    const todoId = `${sessionId}:todo:${String(sequence).padStart(3, '0')}`
    setIssues((current) => [
      {
        id: todoId,
        identifier: createIssueBoardIdentifier(sequence),
        title: '새 작업',
        description: '담당 에이전트 한 명에게 맡길 작업입니다.',
        status: 'todo',
        priority: 'medium',
        assigneeAgentId: null,
        labels: [],
        comments: [
          {
            id: `${todoId}:comment:001`,
            authorType: 'system',
            authorName: '시스템',
            body: '새 작업이 생성되었습니다.',
            createdAt: now,
          },
        ],
        runs: [],
        documents: [],
        relatedItems: [],
        blockedBy: [],
        createdAt: now,
        updatedAt: now,
        startedAt: null,
        completedAt: null,
        live: false,
      },
      ...current,
    ])
  }

  return (
    <section className="bg-background flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden">
      <header className="border-border/70 flex shrink-0 flex-col gap-3 border-b px-6 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-muted-foreground flex items-center gap-2 text-[11px] font-semibold tracking-widest uppercase">
              <FolderKanban className="h-3.5 w-3.5" />
              작업 보드
            </div>
            <h1 className="text-foreground mt-1 truncate text-xl font-semibold">작업</h1>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              작업 {issues.length}개
            </span>
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              작업당 에이전트 1명
            </span>
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              동시 실행 1개
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 gap-2"
            onClick={createNewTodo}
          >
            <Plus className="h-4 w-4" />새 작업
          </Button>
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="작업 검색..."
              aria-label="작업 검색"
              className="h-9 pl-9"
            />
          </div>
          <div className="ml-auto flex items-center gap-1">
            <div className="border-border bg-muted/20 flex items-center gap-1 rounded-md border p-1">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                className={cn(viewMode === 'list' && 'bg-accent text-foreground')}
                title="목록"
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                className={cn(viewMode === 'board' && 'bg-accent text-foreground')}
                title="보드"
                onClick={() => setViewMode('board')}
              >
                <Columns3 className="h-4 w-4" />
              </Button>
            </div>
            <FilterPopover
              activeFilterCount={activeFilterCount}
              assignees={assignees}
              labels={labels}
              liveOnly={liveOnly}
              selectedAssignees={selectedAssignees}
              selectedLabels={selectedLabels}
              selectedStatuses={selectedStatuses}
              onAssigneesChange={setSelectedAssignees}
              onClear={resetFilters}
              onLabelsChange={setSelectedLabels}
              onLiveOnlyChange={setLiveOnly}
              onStatusesChange={setSelectedStatuses}
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-9 gap-1.5 px-2.5"
              title="정렬"
              onClick={() => setSortField(nextSortField(sortField))}
            >
              <ArrowUpDown className="h-4 w-4" />
              {sortFieldLabel(sortField)}
            </Button>
          </div>
        </div>
      </header>

      {viewMode === 'board' ? (
        <TodoKanbanBoard
          draggedIssueId={draggedIssueId}
          dragOverStatus={dragOverStatus}
          grouped={grouped}
          onDragEnd={(issueId, status) => {
            moveIssue(issueId, status)
            setDraggedIssueId(null)
            setDragOverStatus(null)
          }}
          onDragLeave={() => setDragOverStatus(null)}
          onDragOverStatus={setDragOverStatus}
          onDragReset={() => {
            setDraggedIssueId(null)
            setDragOverStatus(null)
          }}
          onDragStart={setDraggedIssueId}
          onOpenIssue={setSelectedIssueId}
          assignees={assignees}
          labels={labels}
        />
      ) : (
        <TodoListView
          issues={filteredIssues}
          onOpenIssue={setSelectedIssueId}
          assignees={assignees}
          labels={labels}
        />
      )}

      <TodoDetailPanel
        assignees={assignees}
        issue={selectedIssue}
        labels={labels}
        onAssignIssue={assignIssue}
        onAddComment={addIssueComment}
        onCreateLabel={createLabel}
        onMoveStatus={(issueId, status) => moveIssue(issueId, status)}
        onOpenChange={(open) => !open && setSelectedIssueId(null)}
        onUpdateIssue={updateIssue}
      />
    </section>
  )
}

function TodoKanbanBoard({
  draggedIssueId,
  dragOverStatus,
  grouped,
  labels,
  onDragEnd,
  onDragLeave,
  onDragOverStatus,
  onDragReset,
  onDragStart,
  onOpenIssue,
  assignees,
}: {
  draggedIssueId: string | null
  dragOverStatus: IssueBoardStatus | null
  grouped: Record<IssueBoardStatus, IssueBoardIssue[]>
  assignees: BoardAssignee[]
  labels: IssueBoardLabel[]
  onDragEnd: (issueId: string, status: IssueBoardStatus) => void
  onDragLeave: () => void
  onDragOverStatus: (status: IssueBoardStatus) => void
  onDragReset: () => void
  onDragStart: (issueId: string) => void
  onOpenIssue: (issueId: string) => void
}) {
  return (
    <div className="min-h-0 flex-1 overflow-x-auto py-5 pr-16 pl-6">
      <div className="flex min-h-full gap-3 pb-3">
        {ISSUE_BOARD_STATUSES.map((status) => {
          const issues = grouped[status]
          const isOver = dragOverStatus === status
          return (
            <section
              key={status}
              onDragOver={(event) => {
                event.preventDefault()
                onDragOverStatus(status)
              }}
              onDragLeave={onDragLeave}
              onDrop={(event) => {
                event.preventDefault()
                const issueId = event.dataTransfer.getData('text/plain') || draggedIssueId
                if (issueId) onDragEnd(issueId, status)
              }}
              className="flex w-[280px] min-w-[280px] shrink-0 flex-col"
            >
              <div className="mb-1 flex items-center gap-2 px-2 py-2">
                <StatusIcon status={status} />
                <span className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  {issueBoardStatusLabel(status)}
                </span>
                <span className="text-muted-foreground/60 ml-auto text-xs tabular-nums">
                  {issues.length}
                </span>
              </div>
              <div
                className={cn(
                  'min-h-[120px] flex-1 space-y-1 rounded-md p-1 transition-colors',
                  isOver ? 'bg-accent/40' : 'bg-muted/20',
                )}
              >
                {issues.map((issue) => (
                  <TodoCard
                    key={issue.id}
                    issue={issue}
                    assignees={assignees}
                    labels={labels}
                    dragging={draggedIssueId === issue.id}
                    onDragReset={onDragReset}
                    onDragStart={onDragStart}
                    onOpenIssue={onOpenIssue}
                  />
                ))}
              </div>
            </section>
          )
        })}
        <div className="w-12 shrink-0" aria-hidden="true" />
      </div>
    </div>
  )
}

function TodoCard({
  dragging,
  issue,
  labels,
  onDragReset,
  onDragStart,
  onOpenIssue,
  assignees,
}: {
  dragging: boolean
  issue: IssueBoardIssue
  assignees: BoardAssignee[]
  labels: IssueBoardLabel[]
  onDragReset: () => void
  onDragStart: (issueId: string) => void
  onOpenIssue: (issueId: string) => void
}) {
  const assigneeName = assigneeLabel(issue.assigneeAgentId, assignees)
  const issueLabels = resolveIssueLabels(issue.labels, labels)

  return (
    <article
      role="button"
      tabIndex={0}
      draggable
      onClick={() => onOpenIssue(issue.id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onOpenIssue(issue.id)
        }
      }}
      onDragStart={(event) => {
        event.dataTransfer.effectAllowed = 'move'
        event.dataTransfer.setData('text/plain', issue.id)
        onDragStart(issue.id)
      }}
      onDragEnd={onDragReset}
      className={cn(
        'bg-card cursor-grab rounded-md border p-2.5 text-left transition-shadow active:cursor-grabbing',
        dragging ? 'opacity-30' : 'hover:shadow-sm',
      )}
    >
      <div className="mb-1.5 flex items-start gap-1.5">
        <span className="text-muted-foreground shrink-0 font-mono text-xs">{issue.identifier}</span>
        <PriorityPill priority={issue.priority} compact />
      </div>
      <p className="mb-2 line-clamp-2 text-sm leading-snug">{issue.title}</p>
      {issueLabels.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {issueLabels.slice(0, 3).map((label) => (
            <LabelPill key={label.id} label={label} compact />
          ))}
          {issueLabels.length > 3 && (
            <span className="text-muted-foreground text-[11px]">+{issueLabels.length - 3}</span>
          )}
        </div>
      )}
      <div className="flex min-w-0 items-center justify-between gap-2">
        <div className="text-muted-foreground inline-flex min-w-0 items-center gap-1 text-xs">
          <UserRound className="h-3 w-3 shrink-0" />
          <span className="truncate">{assigneeName}</span>
        </div>
        {issue.comments.length > 0 && (
          <span className="text-muted-foreground inline-flex shrink-0 items-center gap-1 text-[11px]">
            <MessageSquare className="h-3 w-3" />
            {issue.comments.length}
          </span>
        )}
      </div>
    </article>
  )
}

function TodoListView({
  issues,
  onOpenIssue,
  assignees,
  labels,
}: {
  issues: IssueBoardIssue[]
  onOpenIssue: (issueId: string) => void
  assignees: BoardAssignee[]
  labels: IssueBoardLabel[]
}) {
  const grouped = ISSUE_BOARD_STATUSES.map((status) => ({
    key: status,
    title: issueBoardStatusLabel(status),
    issues: issues.filter((issue) => issue.status === status),
  })).filter((group) => group.issues.length > 0)

  return (
    <div className="min-h-0 flex-1 overflow-auto py-6 pr-16 pl-6">
      <div className="bg-background/70 overflow-hidden rounded-lg border">
        <div className="text-muted-foreground grid grid-cols-[minmax(18rem,1fr)_5rem_8rem_6rem] items-center gap-3 border-b px-4 py-2 text-[11px] font-semibold tracking-widest uppercase">
          <span>작업</span>
          <span className="text-center">우선순위</span>
          <span>담당자</span>
          <span className="text-right">수정</span>
        </div>
        {issues.length === 0 ? (
          <p className="text-muted-foreground px-4 py-6 text-sm">
            현재 필터나 검색어에 맞는 작업이 없습니다.
          </p>
        ) : (
          grouped.map((group) => (
            <div key={group.key}>
              <div className="text-muted-foreground flex items-center gap-2 border-b px-4 py-3 text-xs font-semibold tracking-wide uppercase">
                <StatusIcon status={group.key} />
                {group.title}
                <span className="ml-auto text-[11px] font-medium normal-case">
                  작업 {group.issues.length}개
                </span>
              </div>
              {group.issues.map((issue) => (
                <TodoListRow
                  key={issue.id}
                  assignees={assignees}
                  issue={issue}
                  labels={labels}
                  onOpenIssue={onOpenIssue}
                />
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function TodoListRow({
  assignees,
  issue,
  labels,
  onOpenIssue,
}: {
  assignees: BoardAssignee[]
  issue: IssueBoardIssue
  labels: IssueBoardLabel[]
  onOpenIssue: (issueId: string) => void
}) {
  const issueLabels = resolveIssueLabels(issue.labels, labels)

  return (
    <button
      type="button"
      onClick={() => onOpenIssue(issue.id)}
      className="hover:bg-accent/30 grid w-full grid-cols-[minmax(18rem,1fr)_5rem_8rem_6rem] items-center gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0"
    >
      <div className="flex min-w-0 items-center gap-2">
        <StatusIcon status={issue.status} />
        <span className="text-muted-foreground shrink-0 font-mono text-xs">{issue.identifier}</span>
        <span className="min-w-0 truncate text-sm font-medium">{issue.title}</span>
        {issueLabels.length > 0 && (
          <span className="hidden min-w-0 flex-wrap gap-1 lg:flex">
            {issueLabels.slice(0, 2).map((label) => (
              <LabelPill key={label.id} label={label} compact />
            ))}
            {issueLabels.length > 2 && (
              <span className="text-muted-foreground text-[11px]">+{issueLabels.length - 2}</span>
            )}
          </span>
        )}
      </div>
      <span className="justify-self-center">
        <PriorityPill priority={issue.priority} compact />
      </span>
      <span className="text-muted-foreground truncate text-xs">
        {assigneeLabel(issue.assigneeAgentId, assignees)}
      </span>
      <span className="text-muted-foreground truncate text-right text-xs">
        {formatRelativeTime(issue.updatedAt)}
      </span>
    </button>
  )
}

function FilterPopover({
  activeFilterCount,
  assignees,
  labels,
  liveOnly,
  selectedAssignees,
  selectedLabels,
  selectedStatuses,
  onAssigneesChange,
  onClear,
  onLabelsChange,
  onLiveOnlyChange,
  onStatusesChange,
}: {
  activeFilterCount: number
  assignees: BoardAssignee[]
  labels: IssueBoardLabel[]
  liveOnly: boolean
  selectedAssignees: string[]
  selectedLabels: string[]
  selectedStatuses: IssueBoardStatus[]
  onAssigneesChange: (value: string[]) => void
  onClear: () => void
  onLabelsChange: (value: string[]) => void
  onLiveOnlyChange: (value: boolean) => void
  onStatusesChange: (value: IssueBoardStatus[]) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="relative h-9 w-9"
          title="필터"
        >
          <Filter className="h-4 w-4" />
          {activeFilterCount > 0 && (
            <span className="bg-primary text-primary-foreground absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[9px] font-bold">
              {activeFilterCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="max-h-[min(520px,calc(100vh-6rem))] w-80 overflow-hidden p-0"
      >
        <div className="flex max-h-[min(520px,calc(100vh-6rem))] flex-col">
          <div className="border-border/70 flex items-center justify-between gap-3 border-b px-3 py-3">
            <div>
              <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
                필터
              </div>
              <div className="text-sm font-medium">표시할 작업</div>
            </div>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground text-xs font-medium"
              onClick={onClear}
            >
              초기화
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-3 py-3">
            <div className="space-y-1.5">
              <span className="text-muted-foreground text-xs">빠른 필터</span>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_FILTERS.map((filter) => {
                  const active = arraysEqual(selectedStatuses, [...filter.statuses])
                  return (
                    <button
                      key={filter.id}
                      type="button"
                      className={cn(
                        'rounded-full border px-2.5 py-1 text-xs transition-colors',
                        active
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground',
                      )}
                      onClick={() => onStatusesChange([...filter.statuses] as IssueBoardStatus[])}
                    >
                      {filter.label}
                    </button>
                  )
                })}
              </div>
            </div>
            <FilterSection title="상태">
              {ISSUE_BOARD_STATUSES.map((status) => (
                <FilterCheck
                  key={status}
                  checked={selectedStatuses.includes(status)}
                  icon={<StatusIcon status={status} />}
                  label={issueBoardStatusLabel(status)}
                  onChange={() => onStatusesChange(toggleValue(selectedStatuses, status))}
                />
              ))}
            </FilterSection>
            <FilterSection title="담당 에이전트">
              {[{ id: '__unassigned', name: '담당자 없음', icon: UserRound }, ...assignees].map(
                (assignee) => (
                  <FilterCheck
                    key={assignee.id}
                    checked={selectedAssignees.includes(assignee.id)}
                    icon={
                      assignee.id === '__unassigned' ? undefined : (
                        <assignee.icon className="h-3.5 w-3.5" />
                      )
                    }
                    label={assignee.name}
                    onChange={() => onAssigneesChange(toggleValue(selectedAssignees, assignee.id))}
                  />
                ),
              )}
            </FilterSection>
            <FilterSection title="라벨">
              <div className="max-h-44 space-y-1 overflow-y-auto pr-1">
                {labels.map((label) => (
                  <FilterCheck
                    key={label.id}
                    checked={selectedLabels.includes(label.id)}
                    icon={
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: label.color }}
                      />
                    }
                    label={label.name}
                    onChange={() => onLabelsChange(toggleValue(selectedLabels, label.id))}
                  />
                ))}
              </div>
            </FilterSection>
            <FilterSection title="실행">
              <FilterCheck
                checked={liveOnly}
                label="실행 중인 작업만"
                onChange={() => onLiveOnlyChange(!liveOnly)}
              />
            </FilterSection>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function FilterSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div>
      <div className="text-muted-foreground mb-2 text-[11px] font-semibold tracking-widest uppercase">
        {title}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  )
}

function FilterCheck({
  checked,
  icon,
  label,
  onChange,
}: {
  checked: boolean
  icon?: ReactNode
  label: string
  onChange: () => void
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      className="hover:bg-accent/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
      onClick={onChange}
    >
      <span
        className={cn(
          'border-input flex h-4 w-4 shrink-0 items-center justify-center rounded-[3px] border',
          checked && 'border-primary bg-primary text-primary-foreground',
        )}
      >
        {checked && <Check className="h-3 w-3" />}
      </span>
      <span className="flex min-w-0 flex-1 items-center gap-2">
        {icon}
        <span className="truncate">{label}</span>
      </span>
    </button>
  )
}

function StatusIcon({ status }: { status: IssueBoardStatus }) {
  const Icon =
    status === 'done'
      ? CircleCheck
      : status === 'blocked'
        ? PauseCircle
        : status === 'in_progress'
          ? Clock3
          : Circle
  const color =
    status === 'todo'
      ? 'text-blue-500'
      : status === 'in_progress'
        ? 'text-yellow-500'
        : status === 'blocked'
          ? 'text-red-500'
          : 'text-green-500'

  return <Icon className={cn('h-4 w-4 shrink-0', color)} />
}

function TodoDetailPanel({
  assignees,
  issue,
  labels,
  onAssignIssue,
  onAddComment,
  onCreateLabel,
  onMoveStatus,
  onOpenChange,
  onUpdateIssue,
}: {
  assignees: BoardAssignee[]
  issue: IssueBoardIssue | null
  labels: IssueBoardLabel[]
  onAssignIssue: (issueId: string, assigneeAgentId: string | null) => void
  onAddComment: (issueId: string, body: string) => void
  onCreateLabel: (label: IssueBoardLabel) => void
  onMoveStatus: (issueId: string, status: IssueBoardStatus) => void
  onOpenChange: (open: boolean) => void
  onUpdateIssue: (issueId: string, patch: Partial<IssueBoardIssue>) => void
}) {
  const [detailTab, setDetailTab] = useState<DetailTab>('chat')
  const [commentDraft, setCommentDraft] = useState('')

  if (issue === null) return null

  const submitComment = () => {
    if (!commentDraft.trim()) return
    onAddComment(issue.id, commentDraft)
    setCommentDraft('')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/20"
      role="dialog"
      aria-modal="true"
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="작업 상세 닫기"
        onClick={() => onOpenChange(false)}
      />
      <aside className="bg-background relative flex h-full w-[min(760px,100vw)] flex-col border-l shadow-2xl">
        <header className="border-border/70 shrink-0 border-b px-5 py-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs font-medium">
              <StatusIcon status={issue.status} />
              <span className="text-muted-foreground font-mono">{issue.identifier}</span>
              <span className="rounded-full border px-2 py-0.5">
                {issueBoardStatusLabel(issue.status)}
              </span>
              <PriorityPill priority={issue.priority} />
            </div>
            <Button
              type="button"
              aria-label="작업 상세 닫기"
              variant="ghost"
              size="icon-sm"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <input
            value={issue.title}
            onChange={(event) => onUpdateIssue(issue.id, { title: event.target.value })}
            className="text-foreground focus-visible:ring-ring/40 w-full rounded-sm bg-transparent text-xl leading-tight font-semibold outline-none focus-visible:ring-2"
            aria-label="작업 제목"
          />
          <Textarea
            value={issue.description}
            onChange={(event) => onUpdateIssue(issue.id, { description: event.target.value })}
            className="text-muted-foreground mt-2 min-h-20 resize-none border-0 bg-transparent p-0 text-sm leading-relaxed shadow-none focus-visible:ring-0"
            aria-label="작업 설명"
            placeholder="작업 설명 추가..."
          />
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <IssuePropertiesPanel
            assignees={assignees}
            issue={issue}
            labels={labels}
            onAssignIssue={onAssignIssue}
            onCreateLabel={onCreateLabel}
            onMoveStatus={onMoveStatus}
            onUpdateIssue={onUpdateIssue}
          />

          <div className="border-border/70 mt-5 border-t pt-4">
            <div className="mb-3 flex min-w-0 items-center gap-1 overflow-x-auto">
              <DetailTabButton
                active={detailTab === 'chat'}
                icon={<MessageSquare className="h-3.5 w-3.5" />}
                label={`댓글 ${issue.comments.length}`}
                onClick={() => setDetailTab('chat')}
              />
              <DetailTabButton
                active={detailTab === 'runs'}
                icon={<PlayCircle className="h-3.5 w-3.5" />}
                label={`실행 ${issue.runs.length}`}
                onClick={() => setDetailTab('runs')}
              />
              <DetailTabButton
                active={detailTab === 'activity'}
                icon={<Activity className="h-3.5 w-3.5" />}
                label="활동"
                onClick={() => setDetailTab('activity')}
              />
              <DetailTabButton
                active={detailTab === 'related'}
                icon={<ListTree className="h-3.5 w-3.5" />}
                label="관련"
                onClick={() => setDetailTab('related')}
              />
            </div>

            {detailTab === 'chat' && (
              <IssueChatThread
                commentDraft={commentDraft}
                comments={issue.comments}
                onCommentDraftChange={setCommentDraft}
                onSubmit={submitComment}
              />
            )}
            {detailTab === 'runs' && <IssueRunLedger issue={issue} />}
            {detailTab === 'activity' && <IssueActivityTimeline issue={issue} />}
            {detailTab === 'related' && <IssueRelatedPanel issue={issue} />}
          </div>
        </div>
      </aside>
    </div>
  )
}

function IssuePropertiesPanel({
  assignees,
  issue,
  labels,
  onAssignIssue,
  onCreateLabel,
  onMoveStatus,
  onUpdateIssue,
}: {
  assignees: BoardAssignee[]
  issue: IssueBoardIssue
  labels: IssueBoardLabel[]
  onAssignIssue: (issueId: string, assigneeAgentId: string | null) => void
  onCreateLabel: (label: IssueBoardLabel) => void
  onMoveStatus: (issueId: string, status: IssueBoardStatus) => void
  onUpdateIssue: (issueId: string, patch: Partial<IssueBoardIssue>) => void
}) {
  return (
    <section className="grid [grid-template-columns:7rem_minmax(0,1fr)] gap-x-5 gap-y-3 text-sm">
      <TodoProperty label="상태">
        <div className="flex flex-wrap gap-1.5">
          {ISSUE_BOARD_STATUSES.map((status) => (
            <Button
              key={status}
              type="button"
              variant={issue.status === status ? 'secondary' : 'outline'}
              size="sm"
              className="h-8 gap-1.5"
              onClick={() => onMoveStatus(issue.id, status)}
            >
              <StatusIcon status={status} />
              {issueBoardStatusLabel(status)}
            </Button>
          ))}
        </div>
      </TodoProperty>
      <TodoProperty label="우선순위">
        <PriorityPicker
          value={issue.priority}
          onChange={(priority) => onUpdateIssue(issue.id, { priority })}
        />
      </TodoProperty>
      <TodoProperty label="담당">
        <AssigneePicker
          assignees={assignees}
          value={issue.assigneeAgentId}
          onChange={(assigneeAgentId) => onAssignIssue(issue.id, assigneeAgentId)}
        />
      </TodoProperty>
      <TodoProperty label="라벨">
        <LabelPicker
          labels={labels}
          value={issue.labels}
          onChange={(nextLabels) => onUpdateIssue(issue.id, { labels: nextLabels })}
          onCreateLabel={onCreateLabel}
        />
      </TodoProperty>
      <TodoProperty label="실행">
        <span className="inline-flex items-center gap-1.5">
          <PlayCircle className="h-3.5 w-3.5" />
          {issue.live ? '실행 중' : issue.status === 'done' ? '완료' : '대기'}
        </span>
      </TodoProperty>
      {issue.blockedBy.length > 0 && (
        <TodoProperty label="차단 원인">
          <div className="flex flex-col gap-1">
            {issue.blockedBy.map((item) => (
              <RelatedIssuePill key={item.id} item={item} />
            ))}
          </div>
        </TodoProperty>
      )}
      <TodoProperty label="시작">
        {issue.startedAt ? formatRelativeTime(issue.startedAt) : '아직 시작 전'}
      </TodoProperty>
      <TodoProperty label="완료">
        {issue.completedAt ? formatRelativeTime(issue.completedAt) : '미완료'}
      </TodoProperty>
      <TodoProperty label="생성">{formatRelativeTime(issue.createdAt)}</TodoProperty>
      <TodoProperty label="수정">{formatRelativeTime(issue.updatedAt)}</TodoProperty>
    </section>
  )
}

function DetailTabButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean
  icon: ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-md px-3 text-sm transition-colors',
        active
          ? 'bg-accent text-foreground'
          : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
      )}
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  )
}

function IssueChatThread({
  commentDraft,
  comments,
  onCommentDraftChange,
  onSubmit,
}: {
  commentDraft: string
  comments: IssueBoardIssue['comments']
  onCommentDraftChange: (value: string) => void
  onSubmit: () => void
}) {
  return (
    <div className="space-y-3">
      <div className="max-h-[360px] space-y-3 overflow-y-auto pr-1">
        {comments.length === 0 ? (
          <div className="text-muted-foreground rounded-md border p-4 text-sm">
            이 작업에 아직 댓글이 없습니다.
          </div>
        ) : (
          comments.map((comment) => (
            <div key={comment.id} className="rounded-md border p-3">
              <div className="mb-1 flex items-center gap-2 text-xs">
                <span className="font-medium">{comment.authorName}</span>
                <span className="text-muted-foreground">
                  {commentAuthorLabel(comment.authorType)}
                </span>
                <span className="text-muted-foreground ml-auto">
                  {formatRelativeTime(comment.createdAt)}
                </span>
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{comment.body}</p>
            </div>
          ))
        )}
      </div>
      <div className="rounded-md border p-2">
        <Textarea
          value={commentDraft}
          onChange={(event) => onCommentDraftChange(event.target.value)}
          placeholder="실행 시 참고할 작업 댓글 입력..."
          className="min-h-20 resize-none border-0 p-2 shadow-none focus-visible:ring-0"
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
              event.preventDefault()
              onSubmit()
            }
          }}
        />
        <div className="flex items-center justify-between gap-2 px-2 pb-1">
          <span className="text-muted-foreground text-xs">Ctrl/⌘ + Enter로 전송</span>
          <Button type="button" size="sm" className="h-8 gap-1.5" onClick={onSubmit}>
            <Send className="h-3.5 w-3.5" />
            전송
          </Button>
        </div>
      </div>
    </div>
  )
}

function IssueRunLedger({ issue }: { issue: IssueBoardIssue }) {
  return (
    <div className="space-y-2">
      {issue.runs.length === 0 ? (
        <div className="text-muted-foreground rounded-md border p-4 text-sm">
          아직 연결된 실행이 없습니다.
        </div>
      ) : (
        issue.runs.map((run) => (
          <div key={run.id} className="rounded-md border p-3 text-sm">
            <div className="flex min-w-0 items-center gap-2">
              <RunStatusDot status={run.status} />
              <span className="min-w-0 flex-1 truncate font-medium">{run.title}</span>
              <span className="rounded-full border px-2 py-0.5 text-xs">
                {runStatusLabel(run.status)}
              </span>
            </div>
            <p className="text-muted-foreground mt-2 text-xs leading-relaxed">{run.summary}</p>
            <div className="text-muted-foreground mt-2 flex flex-wrap gap-2 text-xs">
              <span>시작 {formatRelativeTime(run.startedAt)}</span>
              <span>완료 {run.finishedAt ? formatRelativeTime(run.finishedAt) : '진행 중'}</span>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function IssueActivityTimeline({ issue }: { issue: IssueBoardIssue }) {
  const activities = [
    {
      id: 'created',
      title: '작업 생성',
      body: `${issue.identifier} 작업이 생성되었습니다.`,
      at: issue.createdAt,
    },
    ...issue.runs.map((run) => ({
      id: run.id,
      title: `실행 ${runStatusLabel(run.status)}`,
      body: run.summary,
      at: run.finishedAt ?? run.startedAt,
    })),
    ...issue.comments.map((comment) => ({
      id: comment.id,
      title: `${comment.authorName} 메시지`,
      body: comment.body,
      at: comment.createdAt,
    })),
  ].sort((left, right) => new Date(right.at).getTime() - new Date(left.at).getTime())

  return (
    <div className="space-y-2">
      {activities.map((activity) => (
        <div key={activity.id} className="flex gap-3 rounded-md border p-3 text-sm">
          <span className="bg-primary mt-1 h-2 w-2 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-2">
              <span className="truncate font-medium">{activity.title}</span>
              <span className="text-muted-foreground ml-auto shrink-0 text-xs">
                {formatRelativeTime(activity.at)}
              </span>
            </div>
            <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">{activity.body}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

function IssueRelatedPanel({ issue }: { issue: IssueBoardIssue }) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <RelatedSection title="차단 항목" icon={<AlertTriangle className="h-4 w-4" />}>
        {issue.blockedBy.length > 0 ? (
          issue.blockedBy.map((item) => <RelatedIssuePill key={item.id} item={item} />)
        ) : (
          <EmptyRelatedText>차단 항목 없음</EmptyRelatedText>
        )}
      </RelatedSection>
      <RelatedSection title="관련 작업" icon={<ListTree className="h-4 w-4" />}>
        {issue.relatedItems.length > 0 ? (
          issue.relatedItems.map((item) => <RelatedIssuePill key={item.id} item={item} />)
        ) : (
          <EmptyRelatedText>관련 작업 없음</EmptyRelatedText>
        )}
      </RelatedSection>
      <RelatedSection title="산출물" icon={<FileText className="h-4 w-4" />}>
        {issue.documents.length > 0 ? (
          issue.documents.map((document) => (
            <div key={document.id} className="rounded-md border p-3">
              <div className="flex min-w-0 items-center gap-2 text-sm font-medium">
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{document.title}</span>
              </div>
              <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">{document.summary}</p>
              <p className="text-muted-foreground mt-2 text-[11px]">
                수정 {formatRelativeTime(document.updatedAt)}
              </p>
            </div>
          ))
        ) : (
          <EmptyRelatedText>산출물 없음</EmptyRelatedText>
        )}
      </RelatedSection>
      <RelatedSection title="실행 정책" icon={<SlidersHorizontal className="h-4 w-4" />}>
        <div className="text-muted-foreground rounded-md border p-3 text-xs">
          담당 에이전트 1명이 이 작업 컨텍스트로 실행합니다. 서버 연결 후 작업 실행, 재개, 중단
          이벤트가 이 영역에 반영됩니다.
        </div>
      </RelatedSection>
    </div>
  )
}

function RelatedSection({
  children,
  icon,
  title,
}: {
  children: ReactNode
  icon: ReactNode
  title: string
}) {
  return (
    <section className="space-y-2">
      <h3 className="text-muted-foreground flex items-center gap-1.5 text-xs font-semibold tracking-widest uppercase">
        {icon}
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </section>
  )
}

function EmptyRelatedText({ children }: { children: ReactNode }) {
  return <div className="text-muted-foreground rounded-md border p-3 text-xs">{children}</div>
}

function RelatedIssuePill({ item }: { item: IssueBoardIssue['relatedItems'][number] }) {
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-md border px-3 py-2 text-sm">
      <StatusIcon status={item.status} />
      <span className="text-muted-foreground shrink-0 font-mono text-xs">{item.identifier}</span>
      <span className="min-w-0 flex-1 truncate">{item.title}</span>
    </div>
  )
}

function TodoProperty({ children, label }: { children: ReactNode; label: string }) {
  return (
    <>
      <div className="text-muted-foreground flex min-h-9 items-center text-xs">{label}</div>
      <div className="text-foreground flex min-h-9 min-w-0 items-center gap-2">{children}</div>
    </>
  )
}

function LabelPicker({
  labels,
  value,
  onChange,
  onCreateLabel,
}: {
  labels: IssueBoardLabel[]
  value: string[]
  onChange: (labelIds: string[]) => void
  onCreateLabel: (label: IssueBoardLabel) => void
}) {
  const [search, setSearch] = useState('')
  const [newLabelName, setNewLabelName] = useState('')
  const [newLabelColor, setNewLabelColor] = useState('#14b8a6')
  const selectedLabels = resolveIssueLabels(value, labels)
  const normalizedSearch = search.trim().toLowerCase()
  const visibleLabels = labels.filter((label) =>
    normalizedSearch ? label.name.toLowerCase().includes(normalizedSearch) : true,
  )
  const toggleLabel = (labelId: string) => onChange(toggleValue(value, labelId))
  const addLabel = () => {
    const name = newLabelName.trim()
    if (!name) return
    const existing = labels.find((label) => label.name.toLowerCase() === name.toLowerCase())
    if (existing) {
      if (!value.includes(existing.id)) onChange([...value, existing.id])
      setNewLabelName('')
      setSearch('')
      return
    }
    const label = {
      id: createLabelIdentifier(name, labels),
      name: name.slice(0, 48),
      color: isHexColor(newLabelColor) ? newLabelColor : '#14b8a6',
    }
    onCreateLabel(label)
    onChange([...value, label.id])
    setNewLabelName('')
    setSearch('')
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="border-input bg-input-background hover:bg-accent/50 flex min-h-9 w-full max-w-md items-center justify-between gap-3 rounded-md border px-3 py-1.5 text-sm"
        >
          {selectedLabels.length > 0 ? (
            <span className="flex min-w-0 flex-wrap gap-1">
              {selectedLabels.slice(0, 3).map((label) => (
                <LabelPill key={label.id} label={label} />
              ))}
              {selectedLabels.length > 3 && (
                <span className="text-muted-foreground text-xs">+{selectedLabels.length - 3}</span>
              )}
            </span>
          ) : (
            <span className="text-muted-foreground inline-flex items-center gap-1.5">
              <Tag className="h-3.5 w-3.5" />
              라벨 없음
            </span>
          )}
          <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-0">
        <div className="border-border/70 border-b p-2">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="라벨 검색..."
            className="h-8"
          />
        </div>
        <div className="max-h-48 space-y-0.5 overflow-y-auto p-1">
          {visibleLabels.length === 0 ? (
            <div className="text-muted-foreground px-2 py-3 text-xs">검색 결과 없음</div>
          ) : (
            visibleLabels.map((label) => {
              const selected = value.includes(label.id)
              return (
                <button
                  key={label.id}
                  type="button"
                  className={cn(
                    'hover:bg-accent/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm',
                    selected && 'bg-accent text-accent-foreground',
                  )}
                  onClick={() => toggleLabel(label.id)}
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: label.color }}
                  />
                  <span className="min-w-0 flex-1 truncate">{label.name}</span>
                  {selected && <Check className="h-3.5 w-3.5 shrink-0" />}
                </button>
              )
            })
          )}
        </div>
        <div className="border-border/70 space-y-2 border-t p-2">
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={newLabelColor}
              onChange={(event) => setNewLabelColor(event.target.value)}
              className="h-8 w-9 shrink-0 rounded border bg-transparent p-0"
              aria-label="새 라벨 색상"
            />
            <Input
              value={newLabelName}
              onChange={(event) => setNewLabelName(event.target.value)}
              placeholder="새 라벨"
              className="h-8"
              maxLength={48}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 w-full gap-1.5"
            disabled={!newLabelName.trim()}
            onClick={addLabel}
          >
            <Plus className="h-3.5 w-3.5" />
            라벨 만들기
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function LabelPill({ compact = false, label }: { compact?: boolean; label: IssueBoardLabel }) {
  return (
    <span
      className={cn(
        'border-border bg-background/70 text-muted-foreground inline-flex max-w-full shrink-0 items-center gap-1 rounded-full border font-medium',
        compact ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
      )}
      title={label.name}
    >
      <span
        className={cn('shrink-0 rounded-full', compact ? 'h-1.5 w-1.5' : 'h-2 w-2')}
        style={{ backgroundColor: label.color }}
      />
      <span className="truncate">{label.name}</span>
    </span>
  )
}

function PriorityPicker({
  value,
  onChange,
}: {
  value: IssueBoardPriority
  onChange: (priority: IssueBoardPriority) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="border-input bg-input-background hover:bg-accent/50 flex h-9 w-full max-w-56 items-center justify-between gap-3 rounded-md border px-3 text-sm"
        >
          <PriorityPill priority={value} />
          <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-48 p-1">
        {ISSUE_BOARD_PRIORITIES.map((priority) => (
          <button
            key={priority}
            type="button"
            className={cn(
              'hover:bg-accent/50 flex h-9 w-full items-center gap-2 rounded-sm px-2 text-sm',
              priority === value && 'bg-accent text-accent-foreground',
            )}
            onClick={() => onChange(priority)}
          >
            <PriorityPill priority={priority} />
            {priority === value && <Check className="ml-auto h-4 w-4" />}
          </button>
        ))}
      </PopoverContent>
    </Popover>
  )
}

function PriorityPill({
  compact = false,
  priority,
}: {
  compact?: boolean
  priority: IssueBoardPriority
}) {
  const Icon =
    priority === 'critical'
      ? AlertTriangle
      : priority === 'high'
        ? ArrowUp
        : priority === 'low'
          ? ArrowDown
          : Minus
  const tone =
    priority === 'critical'
      ? 'text-red-600 dark:text-red-400'
      : priority === 'high'
        ? 'text-orange-600 dark:text-orange-400'
        : priority === 'medium'
          ? 'text-yellow-600 dark:text-yellow-400'
          : 'text-blue-600 dark:text-blue-400'

  return (
    <span
      className={cn(
        'text-muted-foreground inline-flex shrink-0 items-center gap-1.5 font-medium',
        compact ? 'text-xs' : 'text-sm',
      )}
    >
      <Icon className={cn(compact ? 'h-3.5 w-3.5' : 'h-4 w-4', tone)} />
      {issueBoardPriorityLabel(priority)}
    </span>
  )
}

function AssigneePicker({
  assignees,
  value,
  onChange,
}: {
  assignees: BoardAssignee[]
  value: string | null
  onChange: (assigneeAgentId: string | null) => void
}) {
  const options: Array<BoardAssignee | { id: null; name: string; icon: typeof UserRound }> = [
    { id: null, name: '담당자 없음', icon: UserRound },
    ...assignees,
  ]
  const selected = options.find((option) => option.id === value) ?? options[0]
  const SelectedIcon = selected.icon

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="border-input bg-input-background hover:bg-accent/50 flex h-9 w-full items-center justify-between gap-3 rounded-md border px-3 text-sm"
        >
          <span className="flex min-w-0 items-center gap-2">
            <SelectedIcon className="h-4 w-4 shrink-0" />
            <span className="truncate">{selected.name}</span>
          </span>
          <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] p-1">
        <div className="max-h-60 overflow-y-auto">
          {options.map((option) => {
            const OptionIcon = option.icon
            const selectedOption = option.id === value
            return (
              <button
                key={option.id ?? '__unassigned'}
                type="button"
                className={cn(
                  'hover:bg-accent/50 flex h-9 w-full items-center gap-2 rounded-sm px-2 text-sm',
                  selectedOption && 'bg-accent text-accent-foreground',
                )}
                onClick={() => onChange(option.id)}
              >
                <OptionIcon className="h-4 w-4 shrink-0" />
                <span className="min-w-0 flex-1 truncate text-left">{option.name}</span>
                {selectedOption && <Check className="h-4 w-4 shrink-0" />}
              </button>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}

function commentAuthorLabel(authorType: IssueBoardIssue['comments'][number]['authorType']) {
  const labels: Record<IssueBoardIssue['comments'][number]['authorType'], string> = {
    user: '사용자',
    agent: '에이전트',
    system: '시스템',
  }
  return labels[authorType]
}

function runStatusLabel(status: IssueBoardIssue['runs'][number]['status']) {
  const labels: Record<IssueBoardIssue['runs'][number]['status'], string> = {
    queued: '대기',
    running: '실행 중',
    waiting: '대기 요청',
    completed: '완료',
    failed: '실패',
  }
  return labels[status]
}

function RunStatusDot({ status }: { status: IssueBoardIssue['runs'][number]['status'] }) {
  const color =
    status === 'completed'
      ? 'bg-green-500'
      : status === 'failed'
        ? 'bg-red-500'
        : status === 'waiting'
          ? 'bg-amber-500'
          : status === 'running'
            ? 'bg-cyan-500'
            : 'bg-muted-foreground'

  return <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full', color)} />
}

function resolveIssueLabels(labelIds: string[], labels: IssueBoardLabel[]) {
  const labelById = new Map(labels.map((label) => [label.id, label]))
  return labelIds
    .map((labelId) => labelById.get(labelId) ?? createFallbackLabel(labelId))
    .filter((label): label is IssueBoardLabel => Boolean(label))
}

function createFallbackLabel(labelId: string): IssueBoardLabel {
  return {
    id: labelId,
    name: labelId,
    color: '#64748b',
  }
}

function createLabelIdentifier(name: string, labels: IssueBoardLabel[]) {
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

function isHexColor(value: string) {
  return /^#[0-9a-fA-F]{6}$/.test(value)
}

function filterTodos(
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
      issueBoardPriorityLabel(issue.priority),
      ...issueLabels.map((label) => label.name),
      ...issue.comments.map((comment) => comment.body),
      ...issue.runs.map((run) => `${run.title} ${run.summary}`),
    ].some((value) => value.toLowerCase().includes(normalizedQuery))
  })
}

function sortTodos(issues: IssueBoardIssue[], sortField: SortField) {
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

function nextSortField(sortField: SortField): SortField {
  if (sortField === 'updated') return 'status'
  if (sortField === 'status') return 'title'
  return 'updated'
}

function sortFieldLabel(sortField: SortField) {
  const labels: Record<SortField, string> = {
    updated: '최근 수정',
    status: '상태순',
    title: '제목순',
  }
  return labels[sortField]
}

function toggleValue<T>(values: T[], value: T) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

function arraysEqual(left: readonly string[], right: readonly string[]) {
  if (left.length !== right.length) return false
  const leftSorted = [...left].sort()
  const rightSorted = [...right].sort()
  return leftSorted.every((value, index) => value === rightSorted[index])
}

function loadTodoBoardState(storageKey: string, sessionId: string): PersistedTodoBoardState {
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

function saveTodoBoardState(storageKey: string, state: PersistedTodoBoardState) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(state))
  } catch {
    return
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
    isIssueBoardPriority(issue.priority) &&
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

function assigneeLabel(value: string | null, assignees: BoardAssignee[]) {
  if (value === null) return '담당자 없음'
  return assignees.find((assignee) => assignee.id === value)?.name ?? value
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return '알 수 없음'
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60_000))
  if (diffMinutes < 1) return '방금 전'
  if (diffMinutes < 60) return `${diffMinutes}분 전`
  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}시간 전`
  return `${Math.round(diffHours / 24)}일 전`
}

function isIssueBoardStatus(value: unknown): value is IssueBoardStatus {
  return typeof value === 'string' && ISSUE_BOARD_STATUSES.includes(value as IssueBoardStatus)
}

function isIssueBoardPriority(value: unknown): value is IssueBoardPriority {
  return typeof value === 'string' && ISSUE_BOARD_PRIORITIES.includes(value as IssueBoardPriority)
}

function isKnownAssigneeId(value: unknown): value is IssueBoardIssue['assigneeAgentId'] {
  if (value === null) return true
  return typeof value === 'string'
}
