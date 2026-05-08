import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AlertTriangle,
  ArrowUpDown,
  Bot,
  Check,
  Circle,
  CircleCheck,
  Clock3,
  Columns3,
  Filter,
  FolderKanban,
  List,
  PauseCircle,
  Plus,
  Search,
  UserRound,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/components/ui/utils'
import { useSessionStore } from '@/store/useSessionStore'
import {
  ISSUE_BOARD_STATUSES,
  createIssueBoardIdentifier,
  createIssueBoardFixtures,
  groupIssuesByStatus,
  issueBoardStatusLabel,
  moveIssueToStatus,
  type IssueBoardIssue,
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
type BoardAssignee = {
  id: string
  name: string
  icon: typeof UserRound
}

interface PersistedTodoBoardState {
  issues: IssueBoardIssue[]
  query: string
  viewMode: ViewMode
  sortField: SortField
  selectedStatuses: IssueBoardStatus[]
  selectedAssignees: string[]
  liveOnly: boolean
}

export function IssueBoardPanel({ sessionId }: { sessionId: string }) {
  const storageKey = `heygent-task-board:v2:${sessionId}`
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
  const [query, setQuery] = useState(initialState.query)
  const [viewMode, setViewMode] = useState<ViewMode>(initialState.viewMode)
  const [sortField, setSortField] = useState<SortField>(initialState.sortField)
  const [selectedStatuses, setSelectedStatuses] = useState<IssueBoardStatus[]>(
    initialState.selectedStatuses,
  )
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>(
    initialState.selectedAssignees,
  )
  const [liveOnly, setLiveOnly] = useState(initialState.liveOnly)
  const [draggedIssueId, setDraggedIssueId] = useState<string | null>(null)
  const [dragOverStatus, setDragOverStatus] = useState<IssueBoardStatus | null>(null)
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null)

  useEffect(() => {
    saveTodoBoardState(storageKey, {
      issues,
      query,
      viewMode,
      sortField,
      selectedStatuses,
      selectedAssignees,
      liveOnly,
    })
  }, [
    issues,
    liveOnly,
    query,
    selectedAssignees,
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
            liveOnly,
          },
          assignees,
        ),
        sortField,
      ),
    [assignees, issues, liveOnly, query, selectedAssignees, selectedStatuses, sortField],
  )
  const grouped = useMemo(() => groupIssuesByStatus(filteredIssues), [filteredIssues])
  const selectedIssue = selectedIssueId
    ? (issues.find((issue) => issue.id === selectedIssueId) ?? null)
    : null
  const activeFilterCount =
    Number(selectedStatuses.length > 0) + Number(selectedAssignees.length > 0) + Number(liveOnly)

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

  const resetFilters = () => {
    setQuery('')
    setSelectedStatuses([])
    setSelectedAssignees([])
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
        assigneeAgentId: null,
        createdAt: now,
        updatedAt: now,
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
              liveOnly={liveOnly}
              selectedAssignees={selectedAssignees}
              selectedStatuses={selectedStatuses}
              onAssigneesChange={setSelectedAssignees}
              onClear={resetFilters}
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
        />
      ) : (
        <TodoListView
          issues={filteredIssues}
          onOpenIssue={setSelectedIssueId}
          assignees={assignees}
        />
      )}

      <TodoDetailPanel
        assignees={assignees}
        issue={selectedIssue}
        onAssignIssue={assignIssue}
        onMoveStatus={(issueId, status) => moveIssue(issueId, status)}
        onOpenChange={(open) => !open && setSelectedIssueId(null)}
      />
    </section>
  )
}

function TodoKanbanBoard({
  draggedIssueId,
  dragOverStatus,
  grouped,
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
  onDragReset,
  onDragStart,
  onOpenIssue,
  assignees,
}: {
  dragging: boolean
  issue: IssueBoardIssue
  assignees: BoardAssignee[]
  onDragReset: () => void
  onDragStart: (issueId: string) => void
  onOpenIssue: (issueId: string) => void
}) {
  const assigneeName = assigneeLabel(issue.assigneeAgentId, assignees)

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
        {issue.needsNextStep && (
          <span
            className="inline-flex items-center gap-1 rounded-full border border-amber-400/45 bg-amber-50/60 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:border-amber-300/35 dark:bg-amber-400/10 dark:text-amber-300"
            title="다음 조치가 필요합니다"
            aria-label="다음 조치 필요"
          >
            <AlertTriangle className="h-3 w-3" />
            다음 조치
          </span>
        )}
        {issue.live && (
          <span className="relative mt-0.5 flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
          </span>
        )}
      </div>
      <p className="mb-2 line-clamp-2 text-sm leading-snug">{issue.title}</p>
      <div className="text-muted-foreground inline-flex min-w-0 items-center gap-1 text-xs">
        <UserRound className="h-3 w-3 shrink-0" />
        <span className="truncate">{assigneeName}</span>
      </div>
    </article>
  )
}

function TodoListView({
  issues,
  onOpenIssue,
  assignees,
}: {
  issues: IssueBoardIssue[]
  onOpenIssue: (issueId: string) => void
  assignees: BoardAssignee[]
}) {
  const grouped = ISSUE_BOARD_STATUSES.map((status) => ({
    key: status,
    title: issueBoardStatusLabel(status),
    issues: issues.filter((issue) => issue.status === status),
  })).filter((group) => group.issues.length > 0)

  return (
    <div className="min-h-0 flex-1 overflow-auto py-6 pr-16 pl-6">
      <div className="bg-background/70 overflow-hidden rounded-lg border">
        <div className="text-muted-foreground grid grid-cols-[minmax(18rem,1fr)_8rem_6rem] items-center gap-3 border-b px-4 py-2 text-[11px] font-semibold tracking-widest uppercase">
          <span>작업</span>
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
                <button
                  key={issue.id}
                  type="button"
                  onClick={() => onOpenIssue(issue.id)}
                  className="hover:bg-accent/30 grid w-full grid-cols-[minmax(18rem,1fr)_8rem_6rem] items-center gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <StatusIcon status={issue.status} />
                    {issue.live && <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />}
                    <span className="text-muted-foreground shrink-0 font-mono text-xs">
                      {issue.identifier}
                    </span>
                    <span className="truncate text-sm font-medium">{issue.title}</span>
                  </div>
                  <span className="text-muted-foreground truncate text-xs">
                    {assigneeLabel(issue.assigneeAgentId, assignees)}
                  </span>
                  <span className="text-muted-foreground truncate text-right text-xs">
                    {formatRelativeTime(issue.updatedAt)}
                  </span>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function FilterPopover({
  activeFilterCount,
  assignees,
  liveOnly,
  selectedAssignees,
  selectedStatuses,
  onAssigneesChange,
  onClear,
  onLiveOnlyChange,
  onStatusesChange,
}: {
  activeFilterCount: number
  assignees: BoardAssignee[]
  liveOnly: boolean
  selectedAssignees: string[]
  selectedStatuses: IssueBoardStatus[]
  onAssigneesChange: (value: string[]) => void
  onClear: () => void
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
      <PopoverContent align="end" className="w-80 p-0">
        <div className="space-y-4">
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
          <div className="space-y-4 px-3 pb-3">
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
  onAssignIssue,
  onMoveStatus,
  onOpenChange,
}: {
  assignees: BoardAssignee[]
  issue: IssueBoardIssue | null
  onAssignIssue: (issueId: string, assigneeAgentId: string | null) => void
  onMoveStatus: (issueId: string, status: IssueBoardStatus) => void
  onOpenChange: (open: boolean) => void
}) {
  if (issue === null) return null

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
      <aside className="bg-background relative flex h-full w-[min(500px,100vw)] flex-col border-l shadow-2xl">
        <header className="border-border/70 shrink-0 border-b px-5 py-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-muted-foreground flex min-w-0 items-center gap-2 text-xs font-medium">
              <StatusIcon status={issue.status} />
              <span className="font-mono">{issue.identifier}</span>
              <span>{issueBoardStatusLabel(issue.status)}</span>
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
          <h2 className="text-foreground text-xl leading-tight font-semibold">{issue.title}</h2>
          <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{issue.description}</p>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <section className="grid [grid-template-columns:7rem_minmax(0,1fr)] gap-x-5 gap-y-3 text-sm">
            <TodoProperty label="상태">
              <StatusIcon status={issue.status} />
              {issueBoardStatusLabel(issue.status)}
            </TodoProperty>
            <TodoProperty label="담당">
              <span className="inline-flex items-center gap-1.5">
                <UserRound className="h-3.5 w-3.5" />
                {assigneeLabel(issue.assigneeAgentId, assignees)}
              </span>
            </TodoProperty>
            <TodoProperty label="실행">{issue.live ? '실행 중' : '대기'}</TodoProperty>
            <TodoProperty label="생성">{formatRelativeTime(issue.createdAt)}</TodoProperty>
            <TodoProperty label="수정">{formatRelativeTime(issue.updatedAt)}</TodoProperty>
          </section>

          <section className="border-border/70 mt-5 border-t pt-4">
            <div className="text-muted-foreground mb-2 text-[11px] font-semibold tracking-widest uppercase">
              상태 변경
            </div>
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
          </section>

          <section className="border-border/70 mt-5 border-t pt-4">
            <div className="text-muted-foreground mb-2 text-[11px] font-semibold tracking-widest uppercase">
              담당 변경
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Button
                type="button"
                variant={issue.assigneeAgentId === null ? 'secondary' : 'outline'}
                size="sm"
                className="h-8 gap-1.5"
                onClick={() => onAssignIssue(issue.id, null)}
              >
                <UserRound className="h-3.5 w-3.5" />
                담당자 없음
              </Button>
              {assignees.map((assignee) => {
                const AssigneeIcon = assignee.icon
                return (
                  <Button
                    key={assignee.id}
                    type="button"
                    variant={issue.assigneeAgentId === assignee.id ? 'secondary' : 'outline'}
                    size="sm"
                    className="h-8 gap-1.5"
                    onClick={() => onAssignIssue(issue.id, assignee.id)}
                  >
                    <AssigneeIcon className="h-3.5 w-3.5" />
                    {assignee.name}
                  </Button>
                )
              })}
            </div>
          </section>

          <DetailSection title="실행 기록">
            <RunLedgerRow
              status={issue.live ? '실행 중' : issue.status === 'done' ? '완료' : '대기'}
              text={issue.live ? '담당 에이전트가 처리 중입니다.' : '아직 연결된 실행이 없습니다.'}
            />
          </DetailSection>

          <DetailSection title="메모">
            <div className="rounded-md border p-3 text-sm">
              <p className="text-muted-foreground text-xs leading-relaxed">
                실제 서버 연결 후에는 작업별 실행 결과와 사용자가 남긴 메모가 여기에 쌓입니다.
              </p>
            </div>
          </DetailSection>
        </div>
      </aside>
    </div>
  )
}

function TodoProperty({ children, label }: { children: ReactNode; label: string }) {
  return (
    <>
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className="text-foreground flex min-w-0 items-center gap-2">{children}</div>
    </>
  )
}

function DetailSection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="border-border/70 mt-5 border-t pt-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  )
}

function RunLedgerRow({ status, text }: { status: string; text: string }) {
  return (
    <div className="rounded-md border p-3 text-xs">
      <div className="flex items-center gap-2">
        <span>실행</span>
        <span className="rounded-full border px-1.5 py-0.5">{status}</span>
        <span className="text-muted-foreground ml-auto">방금 전</span>
      </div>
      <div className="text-muted-foreground mt-2">{text}</div>
    </div>
  )
}

function filterTodos(
  issues: IssueBoardIssue[],
  filters: {
    query: string
    statuses: IssueBoardStatus[]
    assignees: string[]
    liveOnly: boolean
  },
  assignees: BoardAssignee[],
) {
  const normalizedQuery = filters.query.trim().toLowerCase()
  return issues.filter((issue) => {
    if (filters.liveOnly && !issue.live) return false
    if (filters.statuses.length > 0 && !filters.statuses.includes(issue.status)) return false
    if (filters.assignees.length > 0) {
      if (!issue.assigneeAgentId) return filters.assignees.includes('__unassigned')
      if (!filters.assignees.includes(issue.assigneeAgentId)) return false
    }
    if (!normalizedQuery) return true
    return [
      issue.identifier,
      issue.title,
      issue.description,
      assigneeLabel(issue.assigneeAgentId, assignees),
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
    query: '',
    viewMode: 'list',
    sortField: 'updated',
    selectedStatuses: [],
    selectedAssignees: [],
    liveOnly: false,
  }

  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (raw === null) return fallback
    const parsed = JSON.parse(raw) as Partial<PersistedTodoBoardState>
    return {
      issues: normalizeIssues(parsed.issues, fallback.issues),
      query: typeof parsed.query === 'string' ? parsed.query : fallback.query,
      viewMode:
        parsed.viewMode === 'list' || parsed.viewMode === 'board'
          ? parsed.viewMode
          : fallback.viewMode,
      sortField: normalizeSortField(parsed.sortField, fallback.sortField),
      selectedStatuses: normalizeStatuses(parsed.selectedStatuses),
      selectedAssignees: normalizeAssignees(parsed.selectedAssignees),
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
    typeof issue.createdAt === 'string' &&
    typeof issue.updatedAt === 'string' &&
    typeof issue.live === 'boolean' &&
    (issue.needsNextStep === undefined || typeof issue.needsNextStep === 'boolean')
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

function isKnownAssigneeId(value: unknown): value is IssueBoardIssue['assigneeAgentId'] {
  if (value === null) return true
  return typeof value === 'string'
}
