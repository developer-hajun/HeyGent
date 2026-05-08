import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowDownAZ,
  ArrowUpDown,
  Check,
  Circle,
  CircleCheck,
  CircleSlash2,
  Clock3,
  Columns3,
  Filter,
  FolderKanban,
  List,
  PauseCircle,
  Search,
  UserRound,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/components/ui/utils'
import {
  ISSUE_BOARD_PRIORITY_ORDER,
  ISSUE_BOARD_STATUSES,
  createIssueBoardFixtures,
  groupIssuesByStatus,
  issueBoardStatusLabel,
  moveIssueToStatus,
  type IssueBoardIssue,
  type IssueBoardPriority,
  type IssueBoardStatus,
} from './issueBoardModel'

const ASSIGNEES = [
  { id: 'agent-ceo', name: 'CEO' },
  { id: 'agent-coder', name: 'Builder' },
  { id: 'agent-review', name: 'ReviewBot' },
] as const

const ASSIGNEE_FILTERS = [{ id: '__unassigned', name: 'No assignee' }, ...ASSIGNEES] as const

const QUICK_FILTERS = [
  { id: 'all', label: 'All', statuses: [] },
  { id: 'active', label: 'Active', statuses: ['todo', 'in_progress', 'in_review', 'blocked'] },
  { id: 'backlog', label: 'Backlog', statuses: ['backlog'] },
  { id: 'done', label: 'Done', statuses: ['done', 'cancelled'] },
] as const

const STATUS_FILTER_ORDER: IssueBoardStatus[] = [
  'in_progress',
  'todo',
  'backlog',
  'in_review',
  'blocked',
  'done',
  'cancelled',
]

type ViewMode = 'list' | 'board'
type SortField = 'updated' | 'priority' | 'title'

interface PersistedIssueBoardState {
  issues: IssueBoardIssue[]
  query: string
  viewMode: ViewMode
  selectedStatuses: IssueBoardStatus[]
  selectedPriorities: IssueBoardPriority[]
  selectedAssignees: string[]
  liveOnly: boolean
  sortField: SortField
}

export function IssueBoardPanel({ sessionId }: { sessionId: string }) {
  const storageKey = `heygent-issue-board:${sessionId}`
  const [initialState] = useState(() => loadIssueBoardState(storageKey, sessionId))
  const [issues, setIssues] = useState(initialState.issues)
  const [query, setQuery] = useState(initialState.query)
  const [viewMode, setViewMode] = useState<ViewMode>(initialState.viewMode)
  const [selectedStatuses, setSelectedStatuses] = useState<IssueBoardStatus[]>(
    initialState.selectedStatuses,
  )
  const [selectedPriorities, setSelectedPriorities] = useState<IssueBoardPriority[]>(
    initialState.selectedPriorities,
  )
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>(
    initialState.selectedAssignees,
  )
  const [liveOnly, setLiveOnly] = useState(initialState.liveOnly)
  const [sortField, setSortField] = useState<SortField>(initialState.sortField)
  const [draggedIssueId, setDraggedIssueId] = useState<string | null>(null)
  const [dragOverStatus, setDragOverStatus] = useState<IssueBoardStatus | null>(null)
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null)

  useEffect(() => {
    saveIssueBoardState(storageKey, {
      issues,
      query,
      viewMode,
      selectedStatuses,
      selectedPriorities,
      selectedAssignees,
      liveOnly,
      sortField,
    })
  }, [
    issues,
    liveOnly,
    query,
    selectedAssignees,
    selectedPriorities,
    selectedStatuses,
    sortField,
    storageKey,
    viewMode,
  ])

  const filteredIssues = useMemo(
    () =>
      sortIssues(
        filterIssues(issues, {
          query,
          statuses: selectedStatuses,
          priorities: selectedPriorities,
          assignees: selectedAssignees,
          liveOnly,
        }),
        sortField,
      ),
    [issues, liveOnly, query, selectedAssignees, selectedPriorities, selectedStatuses, sortField],
  )
  const grouped = useMemo(() => groupIssuesByStatus(filteredIssues), [filteredIssues])
  const selectedIssue = selectedIssueId
    ? (issues.find((issue) => issue.id === selectedIssueId) ?? null)
    : null
  const activeFilterCount =
    Number(selectedStatuses.length > 0) +
    Number(selectedPriorities.length > 0) +
    Number(selectedAssignees.length > 0) +
    Number(liveOnly)

  const moveIssue = (issueId: string, status: IssueBoardStatus) => {
    setIssues((current) => moveIssueToStatus(current, issueId, status))
  }
  const resetFilters = () => {
    setQuery('')
    setSelectedStatuses([])
    setSelectedPriorities([])
    setSelectedAssignees([])
    setLiveOnly(false)
  }

  return (
    <section className="bg-background flex h-full min-h-0 flex-col overflow-hidden">
      <header className="border-border/70 flex shrink-0 flex-col gap-3 border-b px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-muted-foreground flex items-center gap-2 text-[11px] font-semibold tracking-widest uppercase">
              <FolderKanban className="h-3.5 w-3.5" />
              Issue board
            </div>
            <h1 className="text-foreground mt-1 truncate text-xl font-semibold">이슈보드</h1>
          </div>
          <div className="border-border bg-muted/20 flex items-center gap-1 rounded-md border p-1">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className={cn(viewMode === 'list' && 'bg-accent text-foreground')}
              title="List"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className={cn(viewMode === 'board' && 'bg-accent text-foreground')}
              title="Board"
              onClick={() => setViewMode('board')}
            >
              <Columns3 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search issues..."
              className="h-9 pl-9"
            />
          </div>
          <FilterPopover
            activeFilterCount={activeFilterCount}
            liveOnly={liveOnly}
            selectedAssignees={selectedAssignees}
            selectedPriorities={selectedPriorities}
            selectedStatuses={selectedStatuses}
            onAssigneesChange={setSelectedAssignees}
            onClear={resetFilters}
            onLiveOnlyChange={setLiveOnly}
            onPrioritiesChange={setSelectedPriorities}
            onStatusesChange={setSelectedStatuses}
          />
          <div className="border-border bg-muted/20 flex items-center gap-1 rounded-md border p-1">
            {QUICK_FILTERS.map((filter) => {
              const active = arraysEqual(selectedStatuses, [...filter.statuses])
              return (
                <button
                  key={filter.id}
                  type="button"
                  className={cn(
                    'rounded-sm px-2.5 py-1.5 text-xs font-medium transition-colors',
                    active
                      ? 'bg-accent text-foreground'
                      : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground',
                  )}
                  onClick={() => setSelectedStatuses([...filter.statuses] as IssueBoardStatus[])}
                >
                  {filter.label}
                </button>
              )
            })}
          </div>
          {viewMode === 'list' && (
            <SortButton sortField={sortField} onSortFieldChange={setSortField} />
          )}
        </div>
      </header>

      {viewMode === 'board' ? (
        <IssueKanbanBoard
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
        />
      ) : (
        <IssueListView issues={filteredIssues} onOpenIssue={setSelectedIssueId} />
      )}
      <IssueDetailDialog
        issue={selectedIssue}
        onMoveStatus={(issueId, status) => moveIssue(issueId, status)}
        onOpenChange={(open) => !open && setSelectedIssueId(null)}
      />
    </section>
  )
}

function IssueKanbanBoard({
  draggedIssueId,
  dragOverStatus,
  grouped,
  onDragEnd,
  onDragLeave,
  onDragOverStatus,
  onDragReset,
  onDragStart,
  onOpenIssue,
}: {
  draggedIssueId: string | null
  dragOverStatus: IssueBoardStatus | null
  grouped: Record<IssueBoardStatus, IssueBoardIssue[]>
  onDragEnd: (issueId: string, status: IssueBoardStatus) => void
  onDragLeave: () => void
  onDragOverStatus: (status: IssueBoardStatus) => void
  onDragReset: () => void
  onDragStart: (issueId: string) => void
  onOpenIssue: (issueId: string) => void
}) {
  return (
    <div className="min-h-0 flex-1 overflow-x-auto px-6 py-5">
      <div className="flex min-h-full gap-3 pb-3">
        {ISSUE_BOARD_STATUSES.map((status) => {
          const issues = grouped[status]
          const isOver = dragOverStatus === status
          const isEmpty = issues.length === 0
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
              className={cn(
                'flex shrink-0 flex-col transition-[width,min-width] duration-150',
                isEmpty && !isOver ? 'w-12 min-w-12' : 'w-[260px] min-w-[260px]',
              )}
            >
              <div
                className={cn(
                  'mb-1 flex items-center gap-2 px-2 py-2',
                  isEmpty && !isOver && 'justify-center',
                )}
                title={isEmpty && !isOver ? issueBoardStatusLabel(status) : undefined}
              >
                <StatusIcon status={status} />
                {(!isEmpty || isOver) && (
                  <>
                    <span className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                      {issueBoardStatusLabel(status)}
                    </span>
                    <span className="text-muted-foreground/60 ml-auto text-xs tabular-nums">
                      {issues.length}
                    </span>
                  </>
                )}
              </div>
              <div
                className={cn(
                  'min-h-[120px] flex-1 space-y-1 rounded-md p-1 transition-colors',
                  isOver ? 'bg-accent/40' : 'bg-muted/20',
                )}
              >
                {issues.map((issue) => (
                  <IssueCard
                    key={issue.id}
                    issue={issue}
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
      </div>
    </div>
  )
}

function IssueCard({
  dragging,
  issue,
  onDragReset,
  onDragStart,
  onOpenIssue,
}: {
  dragging: boolean
  issue: IssueBoardIssue
  onDragReset: () => void
  onDragStart: (issueId: string) => void
  onOpenIssue: (issueId: string) => void
}) {
  const assigneeName = issue.assigneeAgentId
    ? ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)?.name
    : null

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
            title="This issue needs a next step"
            aria-label="Needs next step"
          >
            <AlertTriangle className="h-3 w-3" />
            Next step
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
      <div className="flex min-w-0 items-center gap-2">
        <PriorityIcon priority={issue.priority} />
        {assigneeName ? (
          <span className="text-muted-foreground inline-flex min-w-0 items-center gap-1 text-xs">
            <UserRound className="h-3 w-3 shrink-0" />
            <span className="truncate">{assigneeName}</span>
          </span>
        ) : (
          <span className="text-muted-foreground font-mono text-xs">unassigned</span>
        )}
      </div>
    </article>
  )
}

function IssueListView({
  issues,
  onOpenIssue,
}: {
  issues: IssueBoardIssue[]
  onOpenIssue: (issueId: string) => void
}) {
  return (
    <div className="min-h-0 flex-1 overflow-auto p-6">
      <div className="bg-background/70 overflow-hidden rounded-lg border">
        {issues.length === 0 ? (
          <p className="text-muted-foreground px-4 py-6 text-sm">
            No issues match the current filters or search.
          </p>
        ) : (
          issues.map((issue) => (
            <button
              key={issue.id}
              type="button"
              onClick={() => onOpenIssue(issue.id)}
              className="hover:bg-accent/30 grid w-full grid-cols-[minmax(0,1fr)_7rem_6rem_8rem] items-center gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0"
            >
              <div className="flex min-w-0 items-center gap-2">
                <StatusIcon status={issue.status} />
                {issue.live && <span className="h-2 w-2 rounded-full bg-blue-500" />}
                <span className="text-muted-foreground font-mono text-xs">{issue.identifier}</span>
                <span className="truncate text-sm font-medium">{issue.title}</span>
              </div>
              <PriorityIcon priority={issue.priority} showLabel />
              <span className="text-muted-foreground text-xs">
                {issueBoardStatusLabel(issue.status)}
              </span>
              <span className="text-muted-foreground truncate text-xs">
                {issue.assigneeAgentId
                  ? ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)?.name
                  : 'unassigned'}
              </span>
            </button>
          ))
        )}
      </div>
    </div>
  )
}

function FilterPopover({
  activeFilterCount,
  liveOnly,
  selectedAssignees,
  selectedPriorities,
  selectedStatuses,
  onAssigneesChange,
  onClear,
  onLiveOnlyChange,
  onPrioritiesChange,
  onStatusesChange,
}: {
  activeFilterCount: number
  liveOnly: boolean
  selectedAssignees: string[]
  selectedPriorities: IssueBoardPriority[]
  selectedStatuses: IssueBoardStatus[]
  onAssigneesChange: (value: string[]) => void
  onClear: () => void
  onLiveOnlyChange: (value: boolean) => void
  onPrioritiesChange: (value: IssueBoardPriority[]) => void
  onStatusesChange: (value: IssueBoardStatus[]) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="h-9 gap-2">
          <Filter className="h-4 w-4" />
          Filters
          {activeFilterCount > 0 && (
            <span className="bg-primary text-primary-foreground rounded-full px-1.5 text-[10px] leading-4">
              {activeFilterCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-3">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
              Filters
            </div>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground text-xs font-medium"
              onClick={onClear}
            >
              Clear
            </button>
          </div>
          <FilterSection title="Status">
            {STATUS_FILTER_ORDER.map((status) => (
              <FilterCheck
                key={status}
                checked={selectedStatuses.includes(status)}
                label={issueBoardStatusLabel(status)}
                onChange={() => onStatusesChange(toggleValue(selectedStatuses, status))}
              />
            ))}
          </FilterSection>
          <FilterSection title="Priority">
            {ISSUE_BOARD_PRIORITY_ORDER.map((priority) => (
              <FilterCheck
                key={priority}
                checked={selectedPriorities.includes(priority)}
                label={priorityLabel(priority)}
                onChange={() => onPrioritiesChange(toggleValue(selectedPriorities, priority))}
              />
            ))}
          </FilterSection>
          <FilterSection title="Assignee">
            {ASSIGNEE_FILTERS.map((assignee) => (
              <FilterCheck
                key={assignee.id}
                checked={selectedAssignees.includes(assignee.id)}
                label={assignee.name}
                onChange={() => onAssigneesChange(toggleValue(selectedAssignees, assignee.id))}
              />
            ))}
          </FilterSection>
          <FilterCheck
            checked={liveOnly}
            label="Live runs only"
            onChange={() => onLiveOnlyChange(!liveOnly)}
          />
        </div>
      </PopoverContent>
    </Popover>
  )
}

function FilterSection({ children, title }: { children: React.ReactNode; title: string }) {
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
  label,
  onChange,
}: {
  checked: boolean
  label: string
  onChange: () => void
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      className="hover:bg-accent/50 flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-sm"
      onClick={onChange}
    >
      <span>{label}</span>
      {checked && <Check className="h-3.5 w-3.5" />}
    </button>
  )
}

function SortButton({
  sortField,
  onSortFieldChange,
}: {
  sortField: SortField
  onSortFieldChange: (value: SortField) => void
}) {
  const next = sortField === 'updated' ? 'priority' : sortField === 'priority' ? 'title' : 'updated'
  const Icon = sortField === 'title' ? ArrowDownAZ : ArrowUpDown

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className="h-9 gap-2"
      onClick={() => onSortFieldChange(next)}
    >
      <Icon className="h-4 w-4" />
      {sortField === 'updated' ? 'Updated' : sortField === 'priority' ? 'Priority' : 'Title'}
    </Button>
  )
}

function StatusIcon({ status }: { status: IssueBoardStatus }) {
  const Icon =
    status === 'done'
      ? CircleCheck
      : status === 'blocked'
        ? PauseCircle
        : status === 'cancelled'
          ? CircleSlash2
          : status === 'in_progress'
            ? Clock3
            : Circle
  const color =
    status === 'backlog'
      ? 'text-muted-foreground/70'
      : status === 'todo'
        ? 'text-blue-500'
        : status === 'in_progress'
          ? 'text-yellow-500'
          : status === 'in_review'
            ? 'text-violet-500'
            : status === 'done'
              ? 'text-green-500'
              : status === 'blocked'
                ? 'text-red-500'
                : 'text-neutral-400'

  return <Icon className={cn('h-4 w-4 shrink-0', color)} />
}

function PriorityIcon({
  priority,
  showLabel = false,
}: {
  priority: IssueBoardPriority
  showLabel?: boolean
}) {
  const color =
    priority === 'critical'
      ? 'bg-red-500'
      : priority === 'high'
        ? 'bg-orange-500'
        : priority === 'medium'
          ? 'bg-blue-500'
          : 'bg-neutral-400'

  return (
    <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
      <span className={cn('h-2 w-2 rounded-full', color)} />
      {showLabel && priorityLabel(priority)}
    </span>
  )
}

function IssueDetailDialog({
  issue,
  onMoveStatus,
  onOpenChange,
}: {
  issue: IssueBoardIssue | null
  onMoveStatus: (issueId: string, status: IssueBoardStatus) => void
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={issue !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        {issue !== null && (
          <>
            <DialogHeader>
              <div className="text-muted-foreground flex items-center gap-2 text-xs font-medium">
                <StatusIcon status={issue.status} />
                <span className="font-mono">{issue.identifier}</span>
                <span>{issueBoardStatusLabel(issue.status)}</span>
              </div>
              <DialogTitle>{issue.title}</DialogTitle>
              <DialogDescription>{issue.description}</DialogDescription>
            </DialogHeader>
            <div className="grid gap-3 text-sm sm:grid-cols-3">
              <IssueDetailMeta label="Priority">
                <PriorityIcon priority={issue.priority} showLabel />
              </IssueDetailMeta>
              <IssueDetailMeta label="Assignee">
                {issue.assigneeAgentId
                  ? ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)?.name
                  : 'unassigned'}
              </IssueDetailMeta>
              <IssueDetailMeta label="Activity">
                {issue.live ? 'Live' : formatRelativeTime(issue.updatedAt)}
              </IssueDetailMeta>
            </div>
            <div className="border-border/70 border-t pt-4">
              <div className="text-muted-foreground mb-2 text-[11px] font-semibold tracking-widest uppercase">
                Move to
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
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

function IssueDetailMeta({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="bg-muted/20 rounded-md border px-3 py-2">
      <div className="text-muted-foreground mb-1 text-[11px] font-semibold tracking-widest uppercase">
        {label}
      </div>
      <div className="text-foreground min-h-5">{children}</div>
    </div>
  )
}

function priorityLabel(priority: IssueBoardPriority) {
  return priority.replace(/\b\w/g, (char) => char.toUpperCase())
}

function filterIssues(
  issues: IssueBoardIssue[],
  filters: {
    query: string
    statuses: IssueBoardStatus[]
    priorities: IssueBoardPriority[]
    assignees: string[]
    liveOnly: boolean
  },
) {
  const normalizedQuery = filters.query.trim().toLowerCase()
  return issues.filter((issue) => {
    if (filters.liveOnly && !issue.live) return false
    if (filters.statuses.length > 0 && !filters.statuses.includes(issue.status)) return false
    if (filters.priorities.length > 0 && !filters.priorities.includes(issue.priority)) return false
    if (filters.assignees.length > 0) {
      if (!issue.assigneeAgentId) return filters.assignees.includes('__unassigned')
      if (!filters.assignees.includes(issue.assigneeAgentId)) return false
    }
    if (!normalizedQuery) return true
    return [issue.identifier, issue.title, issue.description].some((value) =>
      value.toLowerCase().includes(normalizedQuery),
    )
  })
}

function sortIssues(issues: IssueBoardIssue[], sortField: SortField) {
  return [...issues].sort((left, right) => {
    if (sortField === 'priority') {
      return (
        ISSUE_BOARD_PRIORITY_ORDER.indexOf(left.priority) -
        ISSUE_BOARD_PRIORITY_ORDER.indexOf(right.priority)
      )
    }
    if (sortField === 'title') {
      return left.title.localeCompare(right.title)
    }
    return new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime()
  })
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

function loadIssueBoardState(storageKey: string, sessionId: string): PersistedIssueBoardState {
  const fallback: PersistedIssueBoardState = {
    issues: createIssueBoardFixtures(sessionId),
    query: '',
    viewMode: 'board',
    selectedStatuses: [],
    selectedPriorities: [],
    selectedAssignees: [],
    liveOnly: false,
    sortField: 'updated',
  }

  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(storageKey)
    if (raw === null) return fallback
    const parsed = JSON.parse(raw) as Partial<PersistedIssueBoardState>
    return {
      issues: normalizeIssues(parsed.issues, fallback.issues),
      query: typeof parsed.query === 'string' ? parsed.query : fallback.query,
      viewMode:
        parsed.viewMode === 'list' || parsed.viewMode === 'board'
          ? parsed.viewMode
          : fallback.viewMode,
      selectedStatuses: normalizeStatuses(parsed.selectedStatuses),
      selectedPriorities: normalizePriorities(parsed.selectedPriorities),
      selectedAssignees: normalizeAssignees(parsed.selectedAssignees),
      liveOnly: parsed.liveOnly === true,
      sortField:
        parsed.sortField === 'updated' ||
        parsed.sortField === 'priority' ||
        parsed.sortField === 'title'
          ? parsed.sortField
          : fallback.sortField,
    }
  } catch {
    return fallback
  }
}

function saveIssueBoardState(storageKey: string, state: PersistedIssueBoardState) {
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
    isIssueBoardPriority(issue.priority) &&
    isKnownAssigneeId(issue.assigneeAgentId) &&
    typeof issue.createdAt === 'string' &&
    typeof issue.updatedAt === 'string' &&
    typeof issue.live === 'boolean' &&
    (issue.needsNextStep === undefined || typeof issue.needsNextStep === 'boolean')
  )
}

function normalizeAssignees(value: unknown): string[] {
  const allowed = new Set<string>(ASSIGNEE_FILTERS.map((assignee) => assignee.id))
  return normalizeStringArray(value).filter((item) => allowed.has(item))
}

function isKnownAssigneeId(value: unknown): value is IssueBoardIssue['assigneeAgentId'] {
  if (value === null) return true
  if (typeof value !== 'string') return false
  return ASSIGNEES.some((assignee) => assignee.id === value)
}

function normalizeStatuses(value: unknown): IssueBoardStatus[] {
  return normalizeStringArray(value).filter((item): item is IssueBoardStatus =>
    isIssueBoardStatus(item),
  )
}

function normalizePriorities(value: unknown): IssueBoardPriority[] {
  return normalizeStringArray(value).filter((item): item is IssueBoardPriority =>
    isIssueBoardPriority(item),
  )
}

function normalizeStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return 'unknown'
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60_000))
  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return `${Math.round(diffHours / 24)}d ago`
}

function isIssueBoardStatus(value: unknown): value is IssueBoardStatus {
  return typeof value === 'string' && ISSUE_BOARD_STATUSES.includes(value as IssueBoardStatus)
}

function isIssueBoardPriority(value: unknown): value is IssueBoardPriority {
  return (
    typeof value === 'string' && ISSUE_BOARD_PRIORITY_ORDER.includes(value as IssueBoardPriority)
  )
}
