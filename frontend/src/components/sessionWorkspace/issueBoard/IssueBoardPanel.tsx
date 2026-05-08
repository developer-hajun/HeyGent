import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AlertTriangle,
  ArrowDownAZ,
  ArrowUpDown,
  Bot,
  Check,
  ChevronDown,
  Copy,
  Circle,
  CircleCheck,
  CircleSlash2,
  Clock3,
  Columns3,
  Filter,
  FolderKanban,
  HardDrive,
  Layers,
  List,
  ListTree,
  PauseCircle,
  Plus,
  Search,
  SlidersHorizontal,
  Tag,
  UserRound,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/components/ui/utils'
import {
  ISSUE_BOARD_PRIORITY_ORDER,
  ISSUE_BOARD_STATUSES,
  createIssueBoardIdentifier,
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

const CREATORS = [
  { id: 'user:operator', name: 'Operator', icon: UserRound },
  { id: 'agent:builder', name: 'Builder', icon: Bot },
] as const

const PROJECTS = [
  { id: 'project-board', name: 'Board UI', color: 'bg-teal-500' },
  { id: 'project-runtime', name: 'Agent Runtime', color: 'bg-amber-500' },
] as const

const WORKSPACES = [
  { id: 'workspace-session', name: 'Session workspace' },
  { id: 'workspace-isolated', name: 'Isolated workspace' },
] as const

const LABELS = [
  { id: 'ui', name: 'UI', color: 'bg-teal-500' },
  { id: 'api', name: 'API', color: 'bg-blue-500' },
  { id: 'risk', name: 'Risk', color: 'bg-red-500' },
  { id: 'docs', name: 'Docs', color: 'bg-violet-500' },
] as const

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
type IssueColumn =
  | 'status'
  | 'id'
  | 'assignee'
  | 'project'
  | 'workspace'
  | 'parent'
  | 'labels'
  | 'updated'
type GroupBy = 'status' | 'priority' | 'assignee' | 'project' | 'workspace' | 'parent' | 'none'

interface PersistedIssueBoardState {
  issues: IssueBoardIssue[]
  query: string
  viewMode: ViewMode
  selectedStatuses: IssueBoardStatus[]
  selectedPriorities: IssueBoardPriority[]
  selectedAssignees: string[]
  selectedCreators: string[]
  selectedProjects: string[]
  selectedWorkspaces: string[]
  selectedLabels: string[]
  liveOnly: boolean
  sortField: SortField
  groupBy: GroupBy
  nestingEnabled: boolean
  visibleColumns: IssueColumn[]
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
  const [selectedCreators, setSelectedCreators] = useState<string[]>(initialState.selectedCreators)
  const [selectedProjects, setSelectedProjects] = useState<string[]>(initialState.selectedProjects)
  const [selectedWorkspaces, setSelectedWorkspaces] = useState<string[]>(
    initialState.selectedWorkspaces,
  )
  const [selectedLabels, setSelectedLabels] = useState<string[]>(initialState.selectedLabels)
  const [liveOnly, setLiveOnly] = useState(initialState.liveOnly)
  const [sortField, setSortField] = useState<SortField>(initialState.sortField)
  const [groupBy, setGroupBy] = useState<GroupBy>(initialState.groupBy)
  const [nestingEnabled, setNestingEnabled] = useState(initialState.nestingEnabled)
  const [visibleColumns, setVisibleColumns] = useState<IssueColumn[]>(initialState.visibleColumns)
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
      selectedCreators,
      selectedProjects,
      selectedWorkspaces,
      selectedLabels,
      liveOnly,
      sortField,
      groupBy,
      nestingEnabled,
      visibleColumns,
    })
  }, [
    groupBy,
    issues,
    liveOnly,
    nestingEnabled,
    query,
    selectedAssignees,
    selectedCreators,
    selectedLabels,
    selectedPriorities,
    selectedProjects,
    selectedStatuses,
    selectedWorkspaces,
    sortField,
    storageKey,
    visibleColumns,
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
          creators: selectedCreators,
          projects: selectedProjects,
          workspaces: selectedWorkspaces,
          labels: selectedLabels,
          liveOnly,
        }),
        sortField,
      ),
    [
      issues,
      liveOnly,
      query,
      selectedAssignees,
      selectedCreators,
      selectedLabels,
      selectedPriorities,
      selectedProjects,
      selectedStatuses,
      selectedWorkspaces,
      sortField,
    ],
  )
  const grouped = useMemo(() => groupIssuesByStatus(filteredIssues), [filteredIssues])
  const selectedIssue = selectedIssueId
    ? (issues.find((issue) => issue.id === selectedIssueId) ?? null)
    : null
  const activeFilterCount =
    Number(selectedStatuses.length > 0) +
    Number(selectedPriorities.length > 0) +
    Number(selectedAssignees.length > 0) +
    Number(selectedCreators.length > 0) +
    Number(selectedProjects.length > 0) +
    Number(selectedWorkspaces.length > 0) +
    Number(selectedLabels.length > 0) +
    Number(liveOnly)

  const moveIssue = (issueId: string, status: IssueBoardStatus) => {
    setIssues((current) => moveIssueToStatus(current, issueId, status))
  }
  const resetFilters = () => {
    setQuery('')
    setSelectedStatuses([])
    setSelectedPriorities([])
    setSelectedAssignees([])
    setSelectedCreators([])
    setSelectedProjects([])
    setSelectedWorkspaces([])
    setSelectedLabels([])
    setLiveOnly(false)
  }

  const createNewIssue = () => {
    const now = new Date().toISOString()
    const sequence = issues.length + 1
    const issueId = `${sessionId}:issue:${String(sequence).padStart(3, '0')}`
    setIssues((current) => [
      {
        id: issueId,
        identifier: createIssueBoardIdentifier(sessionId, sequence),
        title: 'New operator issue',
        description: '새 작업 항목입니다. 실제 이슈 API가 연결되면 생성 입력으로 대체됩니다.',
        status: 'backlog',
        priority: 'medium',
        assigneeAgentId: null,
        creatorId: 'user:operator',
        projectId: 'project-board',
        workspaceId: 'workspace-session',
        labels: ['ui'],
        createdAt: now,
        updatedAt: now,
        live: false,
      },
      ...current,
    ])
  }

  return (
    <section className="bg-background flex h-full min-h-0 flex-col overflow-hidden">
      <header className="border-border/70 flex shrink-0 flex-col gap-3 border-b px-6 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-muted-foreground flex items-center gap-2 text-[11px] font-semibold tracking-widest uppercase">
              <FolderKanban className="h-3.5 w-3.5" />
              Issue board
            </div>
            <h1 className="text-foreground mt-1 truncate text-xl font-semibold">이슈보드</h1>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              {issues.length} issues
            </span>
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              {ASSIGNEES.length} agents
            </span>
            <span className="border-border bg-muted/20 rounded-full border px-2 py-1 text-[11px] font-medium">
              session aware
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 gap-2"
            onClick={createNewIssue}
          >
            <Plus className="h-4 w-4" />
            New issue
          </Button>
          <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
            <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search issues..."
              aria-label="Search issues"
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
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className={cn('h-9 w-9', nestingEnabled && 'bg-accent text-foreground')}
              title="Nesting"
              onClick={() => setNestingEnabled((value) => !value)}
            >
              <ListTree className="h-4 w-4" />
            </Button>
            <ColumnMenu
              visibleColumns={visibleColumns}
              onVisibleColumnsChange={setVisibleColumns}
            />
            <FilterPopover
              activeFilterCount={activeFilterCount}
              liveOnly={liveOnly}
              selectedAssignees={selectedAssignees}
              selectedCreators={selectedCreators}
              selectedLabels={selectedLabels}
              selectedPriorities={selectedPriorities}
              selectedProjects={selectedProjects}
              selectedStatuses={selectedStatuses}
              selectedWorkspaces={selectedWorkspaces}
              onAssigneesChange={setSelectedAssignees}
              onClear={resetFilters}
              onCreatorsChange={setSelectedCreators}
              onLabelsChange={setSelectedLabels}
              onLiveOnlyChange={setLiveOnly}
              onPrioritiesChange={setSelectedPriorities}
              onProjectsChange={setSelectedProjects}
              onStatusesChange={setSelectedStatuses}
              onWorkspacesChange={setSelectedWorkspaces}
            />
            <SortButton iconOnly sortField={sortField} onSortFieldChange={setSortField} />
            <GroupMenu groupBy={groupBy} onGroupByChange={setGroupBy} />
          </div>
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
        <IssueListView
          issues={filteredIssues}
          onOpenIssue={setSelectedIssueId}
          groupBy={groupBy}
          visibleColumns={visibleColumns}
        />
      )}
      <IssueDetailPanel
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
    <div className="min-h-0 flex-1 overflow-x-auto py-5 pr-16 pl-6">
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
        <div className="w-12 shrink-0" aria-hidden="true" />
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
  groupBy,
  issues,
  onOpenIssue,
  visibleColumns,
}: {
  groupBy: GroupBy
  issues: IssueBoardIssue[]
  onOpenIssue: (issueId: string) => void
  visibleColumns: IssueColumn[]
}) {
  const rows =
    groupBy !== 'none' ? buildIssueGroups(issues, groupBy) : [{ key: 'all', title: null, issues }]

  return (
    <div className="min-h-0 flex-1 overflow-auto py-6 pr-16 pl-6">
      <div className="bg-background/70 overflow-x-auto rounded-lg border">
        <div style={{ minWidth: listMinWidth(visibleColumns), width: '100%' }}>
          <div
            className="text-muted-foreground grid items-center gap-3 border-b px-4 py-2 text-[11px] font-semibold tracking-widest uppercase"
            style={{ gridTemplateColumns: listGridTemplate(visibleColumns) }}
          >
            <span>Issue</span>
            {visibleColumns.includes('status') && <span>Status</span>}
            {visibleColumns.includes('id') && <span>ID</span>}
            {visibleColumns.includes('assignee') && <span>Assignee</span>}
            {visibleColumns.includes('project') && <span>Project</span>}
            {visibleColumns.includes('workspace') && <span>Workspace</span>}
            {visibleColumns.includes('labels') && <span>Tags</span>}
            {visibleColumns.includes('updated') && <span className="text-right">Updated</span>}
          </div>
          {issues.length === 0 ? (
            <p className="text-muted-foreground px-4 py-6 text-sm">
              No issues match the current filters or search.
            </p>
          ) : (
            rows.map((group) => (
              <div key={group.key}>
                {group.title && (
                  <div className="text-muted-foreground flex items-center gap-2 border-b px-4 py-3 text-xs font-semibold tracking-wide uppercase">
                    <StatusIcon status={group.key as IssueBoardStatus} />
                    {group.title}
                    <span className="ml-auto text-[11px] font-medium normal-case">
                      {group.issues.length} issue{group.issues.length === 1 ? '' : 's'}
                    </span>
                    <button
                      type="button"
                      className="hover:bg-accent rounded p-0.5"
                      aria-label={`Add issue to ${group.title}`}
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
                {group.issues.map((issue) => (
                  <button
                    key={issue.id}
                    type="button"
                    onClick={() => onOpenIssue(issue.id)}
                    className="hover:bg-accent/30 grid w-full items-center gap-3 border-b px-4 py-3 text-left transition-colors last:border-b-0"
                    style={{ gridTemplateColumns: listGridTemplate(visibleColumns) }}
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <StatusIcon status={issue.status} />
                      {issue.live && <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />}
                      <span className="text-muted-foreground shrink-0 font-mono text-xs">
                        {issue.identifier}
                      </span>
                      <span className="truncate text-sm font-medium">{issue.title}</span>
                    </div>
                    {visibleColumns.includes('status') && (
                      <span className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
                        <StatusIcon status={issue.status} />
                        {issueBoardStatusLabel(issue.status)}
                      </span>
                    )}
                    {visibleColumns.includes('id') && (
                      <span className="text-muted-foreground shrink-0 font-mono text-xs">
                        {issue.identifier}
                      </span>
                    )}
                    {visibleColumns.includes('assignee') && (
                      <span className="text-muted-foreground truncate text-xs">
                        {issue.assigneeAgentId
                          ? ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)
                              ?.name
                          : 'unassigned'}
                      </span>
                    )}
                    {visibleColumns.includes('project') && (
                      <IssueProjectPill projectId={issue.projectId} />
                    )}
                    {visibleColumns.includes('workspace') && (
                      <span className="text-muted-foreground truncate text-xs">
                        {WORKSPACES.find((workspace) => workspace.id === issue.workspaceId)?.name ??
                          ''}
                      </span>
                    )}
                    {visibleColumns.includes('parent') && (
                      <span className="text-muted-foreground truncate text-xs">No parent</span>
                    )}
                    {visibleColumns.includes('labels') && <IssueLabelPills labels={issue.labels} />}
                    {visibleColumns.includes('updated') && (
                      <span className="text-muted-foreground truncate text-right text-xs">
                        {formatRelativeTime(issue.updatedAt)}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function listGridTemplate(visibleColumns: IssueColumn[]) {
  const columnWidths: Record<IssueColumn, string> = {
    status: 'minmax(4.75rem,6rem)',
    id: 'minmax(4.25rem,5rem)',
    assignee: 'minmax(5rem,6.5rem)',
    project: 'minmax(5rem,6.5rem)',
    workspace: 'minmax(6.25rem,8rem)',
    parent: 'minmax(3.75rem,5rem)',
    labels: 'minmax(3.75rem,6rem)',
    updated: 'minmax(3.75rem,4.75rem)',
  }
  return ['minmax(18rem,1fr)', ...visibleColumns.map((column) => columnWidths[column])].join(' ')
}

function listMinWidth(visibleColumns: IssueColumn[]) {
  return visibleColumns.length > 3 ? '1040px' : '760px'
}

function buildIssueGroups(issues: IssueBoardIssue[], groupBy: GroupBy) {
  if (groupBy === 'status') {
    return ISSUE_BOARD_STATUSES.map((status) => ({
      key: status,
      title: issueBoardStatusLabel(status),
      issues: issues.filter((issue) => issue.status === status),
    })).filter((group) => group.issues.length > 0)
  }

  const groups = new Map<string, { key: string; title: string; issues: IssueBoardIssue[] }>()
  for (const issue of issues) {
    const key = resolveGroupKey(issue, groupBy)
    const title = resolveGroupTitle(issue, groupBy)
    const group = groups.get(key)
    if (group) {
      group.issues.push(issue)
    } else {
      groups.set(key, { key, title, issues: [issue] })
    }
  }
  return [...groups.values()]
}

function resolveGroupKey(issue: IssueBoardIssue, groupBy: GroupBy) {
  if (groupBy === 'priority') return issue.priority
  if (groupBy === 'assignee') return issue.assigneeAgentId ?? 'unassigned'
  if (groupBy === 'project') return issue.projectId ?? 'no-project'
  if (groupBy === 'workspace') return issue.workspaceId ?? 'no-workspace'
  if (groupBy === 'parent') return 'no-parent'
  return issue.status
}

function resolveGroupTitle(issue: IssueBoardIssue, groupBy: GroupBy) {
  if (groupBy === 'priority') return `${priorityLabel(issue.priority)} priority`
  if (groupBy === 'assignee') {
    if (!issue.assigneeAgentId) return 'Unassigned'
    return (
      ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)?.name ??
      issue.assigneeAgentId
    )
  }
  if (groupBy === 'project') {
    return PROJECTS.find((project) => project.id === issue.projectId)?.name ?? 'No project'
  }
  if (groupBy === 'workspace') {
    return (
      WORKSPACES.find((workspace) => workspace.id === issue.workspaceId)?.name ?? 'No workspace'
    )
  }
  if (groupBy === 'parent') return 'No parent'
  return issueBoardStatusLabel(issue.status)
}

function FilterPopover({
  activeFilterCount,
  liveOnly,
  selectedAssignees,
  selectedCreators,
  selectedLabels,
  selectedPriorities,
  selectedProjects,
  selectedStatuses,
  selectedWorkspaces,
  onAssigneesChange,
  onClear,
  onCreatorsChange,
  onLabelsChange,
  onLiveOnlyChange,
  onPrioritiesChange,
  onProjectsChange,
  onStatusesChange,
  onWorkspacesChange,
}: {
  activeFilterCount: number
  liveOnly: boolean
  selectedAssignees: string[]
  selectedCreators: string[]
  selectedLabels: string[]
  selectedPriorities: IssueBoardPriority[]
  selectedProjects: string[]
  selectedStatuses: IssueBoardStatus[]
  selectedWorkspaces: string[]
  onAssigneesChange: (value: string[]) => void
  onClear: () => void
  onCreatorsChange: (value: string[]) => void
  onLabelsChange: (value: string[]) => void
  onLiveOnlyChange: (value: boolean) => void
  onPrioritiesChange: (value: IssueBoardPriority[]) => void
  onProjectsChange: (value: string[]) => void
  onStatusesChange: (value: IssueBoardStatus[]) => void
  onWorkspacesChange: (value: string[]) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="relative h-9 w-9"
          title="Filter"
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
        className="max-h-[min(80vh,42rem)] w-[min(760px,calc(100vw-2rem))] overflow-y-auto p-0"
      >
        <div className="space-y-4">
          <div className="border-border/70 flex items-center justify-between gap-3 border-b px-3 py-3">
            <div>
              <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
                Filters
              </div>
              <div className="text-sm font-medium">Visible issue set</div>
            </div>
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground text-xs font-medium"
              onClick={onClear}
            >
              Clear
            </button>
          </div>
          <div className="space-y-3 px-3 pb-3">
            <div className="space-y-1.5">
              <span className="text-muted-foreground text-xs">Quick filters</span>
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

            <div className="border-border border-t" />

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="min-w-0 space-y-3">
                <FilterSection title="Status">
                  {STATUS_FILTER_ORDER.map((status) => (
                    <FilterCheck
                      key={status}
                      checked={selectedStatuses.includes(status)}
                      icon={<StatusIcon status={status} />}
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
                      icon={<PriorityIcon priority={priority} />}
                      label={priorityLabel(priority)}
                      onChange={() => onPrioritiesChange(toggleValue(selectedPriorities, priority))}
                    />
                  ))}
                </FilterSection>
              </div>

              <div className="min-w-0 space-y-3">
                <FilterSection title="Assignee">
                  {ASSIGNEE_FILTERS.map((assignee) => (
                    <FilterCheck
                      key={assignee.id}
                      checked={selectedAssignees.includes(assignee.id)}
                      icon={
                        assignee.id === '__unassigned' ? undefined : (
                          <UserRound className="h-3.5 w-3.5" />
                        )
                      }
                      label={assignee.name}
                      onChange={() =>
                        onAssigneesChange(toggleValue(selectedAssignees, assignee.id))
                      }
                    />
                  ))}
                </FilterSection>
                <FilterSection title="Creator">
                  {CREATORS.map((creator) => {
                    const Icon = creator.icon
                    return (
                      <FilterCheck
                        key={creator.id}
                        checked={selectedCreators.includes(creator.id)}
                        icon={<Icon className="h-3.5 w-3.5" />}
                        label={creator.name}
                        onChange={() => onCreatorsChange(toggleValue(selectedCreators, creator.id))}
                      />
                    )
                  })}
                </FilterSection>
                <FilterSection title="Project">
                  {PROJECTS.map((project) => (
                    <FilterCheck
                      key={project.id}
                      checked={selectedProjects.includes(project.id)}
                      icon={<span className={cn('h-2.5 w-2.5 rounded-full', project.color)} />}
                      label={project.name}
                      onChange={() => onProjectsChange(toggleValue(selectedProjects, project.id))}
                    />
                  ))}
                </FilterSection>
              </div>

              <div className="min-w-0 space-y-3">
                <FilterSection title="Labels">
                  {LABELS.map((label) => (
                    <FilterCheck
                      key={label.id}
                      checked={selectedLabels.includes(label.id)}
                      icon={<span className={cn('h-2.5 w-2.5 rounded-full', label.color)} />}
                      label={label.name}
                      onChange={() => onLabelsChange(toggleValue(selectedLabels, label.id))}
                    />
                  ))}
                </FilterSection>
                <FilterSection title="Workspace">
                  {WORKSPACES.map((workspace) => (
                    <FilterCheck
                      key={workspace.id}
                      checked={selectedWorkspaces.includes(workspace.id)}
                      icon={<HardDrive className="h-3.5 w-3.5" />}
                      label={workspace.name}
                      onChange={() =>
                        onWorkspacesChange(toggleValue(selectedWorkspaces, workspace.id))
                      }
                    />
                  ))}
                </FilterSection>
                <FilterSection title="Visibility">
                  <FilterCheck
                    checked={liveOnly}
                    label="Live runs only"
                    onChange={() => onLiveOnlyChange(!liveOnly)}
                  />
                </FilterSection>
              </div>
            </div>
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

function SortButton({
  iconOnly = false,
  sortField,
  onSortFieldChange,
}: {
  iconOnly?: boolean
  sortField: SortField
  onSortFieldChange: (value: SortField) => void
}) {
  const next = sortField === 'updated' ? 'priority' : sortField === 'priority' ? 'title' : 'updated'
  const Icon = sortField === 'title' ? ArrowDownAZ : ArrowUpDown

  return (
    <Button
      type="button"
      variant={iconOnly ? 'ghost' : 'outline'}
      size={iconOnly ? 'icon-sm' : 'sm'}
      className={iconOnly ? 'h-9 w-9' : 'h-9 gap-2'}
      title={sortField === 'updated' ? 'Updated' : sortField === 'priority' ? 'Priority' : 'Title'}
      onClick={() => onSortFieldChange(next)}
    >
      <Icon className="h-4 w-4" />
      {!iconOnly &&
        (sortField === 'updated' ? 'Updated' : sortField === 'priority' ? 'Priority' : 'Title')}
    </Button>
  )
}

const COLUMN_LABELS: Record<IssueColumn, string> = {
  status: 'Status',
  id: 'ID',
  assignee: 'Assignee',
  project: 'Project',
  workspace: 'Workspace',
  parent: 'Parent issue',
  labels: 'Tags',
  updated: 'Last updated',
}

const DEFAULT_VISIBLE_COLUMNS: IssueColumn[] = ['assignee', 'workspace', 'updated']

function ColumnMenu({
  visibleColumns,
  onVisibleColumnsChange,
}: {
  visibleColumns: IssueColumn[]
  onVisibleColumnsChange: (columns: IssueColumn[]) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button type="button" variant="ghost" size="icon-sm" className="h-9 w-9" title="Columns">
          <SlidersHorizontal className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 p-2">
        <div className="space-y-2">
          <div className="px-2 py-1">
            <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
              Desktop issue rows
            </div>
            <div className="text-sm font-medium">Columns</div>
          </div>
          {(Object.keys(COLUMN_LABELS) as IssueColumn[]).map((column) => (
            <button
              key={column}
              type="button"
              role="checkbox"
              aria-checked={visibleColumns.includes(column)}
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
              onClick={() => {
                const next = toggleValue(visibleColumns, column)
                onVisibleColumnsChange(next.length > 0 ? next : ['updated'])
              }}
            >
              <Check
                className={cn('h-3.5 w-3.5', !visibleColumns.includes(column) && 'opacity-0')}
              />
              {COLUMN_LABELS[column]}
            </button>
          ))}
          <div className="border-border border-t" />
          <button
            type="button"
            className="hover:bg-accent/50 flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-sm"
            onClick={() => onVisibleColumnsChange(DEFAULT_VISIBLE_COLUMNS)}
          >
            Reset defaults
            <span className="text-muted-foreground text-xs">status, id, updated</span>
          </button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

const GROUP_OPTIONS: { id: GroupBy; label: string }[] = [
  { id: 'status', label: 'Status' },
  { id: 'priority', label: 'Priority' },
  { id: 'assignee', label: 'Assignee' },
  { id: 'project', label: 'Project' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'parent', label: 'Parent Issue' },
  { id: 'none', label: 'None' },
]

function GroupMenu({
  groupBy,
  onGroupByChange,
}: {
  groupBy: GroupBy
  onGroupByChange: (value: GroupBy) => void
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className={cn('h-9 w-9', groupBy !== 'none' && 'bg-accent text-foreground')}
          title="Group"
        >
          <Layers className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-56 p-2">
        <div className="space-y-2">
          <div className="px-2 py-1">
            <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
              Group by
            </div>
            <div className="text-sm font-medium">
              {GROUP_OPTIONS.find((option) => option.id === groupBy)?.label}
            </div>
          </div>
          {GROUP_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm"
              onClick={() => onGroupByChange(option.id)}
            >
              <Check className={cn('h-3.5 w-3.5', groupBy !== option.id && 'opacity-0')} />
              {option.label}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
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

function IssueProjectPill({ projectId }: { projectId: string | null }) {
  const project = PROJECTS.find((option) => option.id === projectId)
  if (!project) return <span className="text-muted-foreground text-xs">No project</span>

  return (
    <span className="inline-flex min-w-0 items-center gap-1.5 text-xs">
      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', project.color)} />
      <span className="truncate">{project.name}</span>
    </span>
  )
}

function IssueLabelPills({ labels }: { labels: string[] }) {
  if (labels.length === 0) return <span className="text-muted-foreground text-xs">No labels</span>

  return (
    <span className="flex min-w-0 flex-wrap gap-1">
      {labels.map((labelId) => {
        const label = LABELS.find((option) => option.id === labelId)
        if (!label) return null
        return (
          <span
            key={label.id}
            className="border-border inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium"
          >
            <Tag className="h-3 w-3" />
            <span className={cn('h-1.5 w-1.5 rounded-full', label.color)} />
            {label.name}
          </span>
        )
      })}
    </span>
  )
}

function IssueDetailPanel({
  issue,
  onMoveStatus,
  onOpenChange,
}: {
  issue: IssueBoardIssue | null
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
        aria-label="Close issue details"
        onClick={() => onOpenChange(false)}
      />
      <aside className="bg-background relative flex h-full w-[min(520px,100vw)] flex-col border-l shadow-2xl">
        <header className="border-border/70 shrink-0 border-b px-5 py-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-muted-foreground flex min-w-0 items-center gap-2 text-xs font-medium">
              <StatusIcon status={issue.status} />
              <span className="font-mono">{issue.identifier}</span>
              <span>{issueBoardStatusLabel(issue.status)}</span>
            </div>
            <Button
              type="button"
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
            <IssueProperty label="Status">
              <StatusIcon status={issue.status} />
              {issueBoardStatusLabel(issue.status)}
            </IssueProperty>
            <IssueProperty label="Priority">
              <PriorityIcon priority={issue.priority} showLabel />
            </IssueProperty>
            <IssueProperty label="Labels">
              <IssueLabelPills labels={issue.labels} />
            </IssueProperty>
            <IssueProperty label="Assignee">
              {issue.assigneeAgentId
                ? ASSIGNEES.find((assignee) => assignee.id === issue.assigneeAgentId)?.name
                : 'unassigned'}
            </IssueProperty>
            <IssueProperty label="Project">
              <IssueProjectPill projectId={issue.projectId} />
            </IssueProperty>
            <IssueProperty label="Parent">No parent</IssueProperty>
            <IssueProperty label="Workspace">
              <span className="inline-flex items-center gap-1.5">
                <HardDrive className="h-3.5 w-3.5" />
                {WORKSPACES.find((workspace) => workspace.id === issue.workspaceId)?.name ??
                  'No workspace'}
              </span>
            </IssueProperty>
            <IssueProperty label="Created">{formatRelativeTime(issue.createdAt)}</IssueProperty>
            <IssueProperty label="Updated">{formatRelativeTime(issue.updatedAt)}</IssueProperty>
          </section>

          <section className="border-border/70 mt-5 border-t pt-4">
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
          </section>

          <DetailSection title="Documents" action="New document">
            <DetailDocument
              kind="plan"
              title="Plan"
              body="정의된 상태와 담당자를 기준으로 다음 실행 단계를 정리합니다."
            />
            <DetailDocument
              kind="notes"
              title="Review Notes"
              body="필터, 상세, 실행 상태가 한 화면에서 확인되는지 검토합니다."
            />
          </DetailSection>

          <DetailSection title="Run ledger" action="Latest run">
            <div className="space-y-2">
              <RunLedgerRow
                status={issue.live ? 'Running' : 'Succeeded'}
                text="Checks after finish"
              />
              <RunLedgerRow status="Succeeded" text="Continuation handoff" />
            </div>
          </DetailSection>

          <DetailSection title="Workspace" action="View tasks">
            <div className="rounded-md border p-3 text-sm">
              <div className="flex items-center gap-2 font-medium">
                <HardDrive className="h-4 w-4" />
                Runtime status
              </div>
              <div className="text-muted-foreground mt-2 grid grid-cols-[5rem_minmax(0,1fr)] gap-y-1 text-xs">
                <span>Branch</span>
                <span className="font-mono">{issue.identifier.toLowerCase()}-workspace</span>
                <span>Path</span>
                <span className="font-mono">~/workspaces/{issue.identifier.toLowerCase()}</span>
                <span>Service</span>
                <span>{issue.live ? 'running' : 'idle'}</span>
              </div>
            </div>
          </DetailSection>
        </div>
      </aside>
    </div>
  )
}

function IssueProperty({ children, label }: { children: ReactNode; label: string }) {
  return (
    <>
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className="text-foreground flex min-w-0 items-center gap-2">{children}</div>
    </>
  )
}

function DetailSection({
  action,
  children,
  title,
}: {
  action: string
  children: ReactNode
  title: string
}) {
  return (
    <section className="border-border/70 mt-5 border-t pt-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        <button type="button" className="text-muted-foreground hover:text-foreground text-xs">
          {action}
        </button>
      </div>
      {children}
    </section>
  )
}

function DetailDocument({ body, kind, title }: { body: string; kind: string; title: string }) {
  return (
    <div className="mb-2 rounded-md border p-3 text-sm">
      <div className="mb-1 flex items-center gap-2">
        <ChevronDown className="h-3.5 w-3.5" />
        <span className="text-muted-foreground rounded border px-1.5 py-0.5 text-[10px] uppercase">
          {kind}
        </span>
        <span className="font-medium">{title}</span>
        <Copy className="text-muted-foreground ml-auto h-3.5 w-3.5" />
      </div>
      <p className="text-muted-foreground text-xs leading-relaxed">{body}</p>
    </div>
  )
}

function RunLedgerRow({ status, text }: { status: string; text: string }) {
  return (
    <div className="rounded-md border p-3 text-xs">
      <div className="flex items-center gap-2">
        <span className="font-mono">run</span>
        <span className="rounded-full border px-1.5 py-0.5">{status}</span>
        <span className="text-muted-foreground ml-auto">just now</span>
      </div>
      <div className="text-muted-foreground mt-2">Next action: {text}</div>
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
    creators: string[]
    projects: string[]
    workspaces: string[]
    labels: string[]
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
    if (filters.creators.length > 0 && !filters.creators.includes(issue.creatorId)) return false
    if (filters.projects.length > 0) {
      if (!issue.projectId || !filters.projects.includes(issue.projectId)) return false
    }
    if (filters.workspaces.length > 0) {
      if (!issue.workspaceId || !filters.workspaces.includes(issue.workspaceId)) return false
    }
    if (
      filters.labels.length > 0 &&
      !filters.labels.some((labelId) => issue.labels.includes(labelId))
    ) {
      return false
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
    viewMode: 'list',
    selectedStatuses: [],
    selectedPriorities: [],
    selectedAssignees: [],
    selectedCreators: [],
    selectedProjects: [],
    selectedWorkspaces: [],
    selectedLabels: [],
    liveOnly: false,
    sortField: 'updated',
    groupBy: 'status',
    nestingEnabled: true,
    visibleColumns: DEFAULT_VISIBLE_COLUMNS,
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
      selectedCreators: normalizeKnownValues(
        parsed.selectedCreators,
        CREATORS.map((creator) => creator.id),
      ),
      selectedProjects: normalizeKnownValues(
        parsed.selectedProjects,
        PROJECTS.map((project) => project.id),
      ),
      selectedWorkspaces: normalizeKnownValues(
        parsed.selectedWorkspaces,
        WORKSPACES.map((workspace) => workspace.id),
      ),
      selectedLabels: normalizeKnownValues(
        parsed.selectedLabels,
        LABELS.map((label) => label.id),
      ),
      liveOnly: parsed.liveOnly === true,
      sortField:
        parsed.sortField === 'updated' ||
        parsed.sortField === 'priority' ||
        parsed.sortField === 'title'
          ? parsed.sortField
          : fallback.sortField,
      groupBy: normalizeGroupBy(parsed.groupBy, fallback.groupBy),
      nestingEnabled:
        typeof parsed.nestingEnabled === 'boolean'
          ? parsed.nestingEnabled
          : fallback.nestingEnabled,
      visibleColumns: normalizeColumns(parsed.visibleColumns, fallback.visibleColumns),
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
    isKnownCreatorId(issue.creatorId) &&
    isKnownNullableOptionId(
      issue.projectId,
      PROJECTS.map((project) => project.id),
    ) &&
    isKnownNullableOptionId(
      issue.workspaceId,
      WORKSPACES.map((workspace) => workspace.id),
    ) &&
    Array.isArray(issue.labels) &&
    issue.labels.every((label) =>
      isKnownOptionId(
        label,
        LABELS.map((option) => option.id),
      ),
    ) &&
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

function normalizeKnownValues(value: unknown, allowedValues: readonly string[]): string[] {
  const allowed = new Set(allowedValues)
  return normalizeStringArray(value).filter((item) => allowed.has(item))
}

function normalizeColumns(value: unknown, fallback: IssueColumn[]): IssueColumn[] {
  const columns = normalizeKnownValues(value, Object.keys(COLUMN_LABELS)) as IssueColumn[]
  return columns.length > 0 ? columns : fallback
}

function normalizeGroupBy(value: unknown, fallback: GroupBy): GroupBy {
  return typeof value === 'string' && GROUP_OPTIONS.some((option) => option.id === value)
    ? (value as GroupBy)
    : fallback
}

function isKnownAssigneeId(value: unknown): value is IssueBoardIssue['assigneeAgentId'] {
  if (value === null) return true
  if (typeof value !== 'string') return false
  return ASSIGNEES.some((assignee) => assignee.id === value)
}

function isKnownCreatorId(value: unknown): value is IssueBoardIssue['creatorId'] {
  return typeof value === 'string' && CREATORS.some((creator) => creator.id === value)
}

function isKnownNullableOptionId(value: unknown, allowedValues: readonly string[]) {
  return value === null || isKnownOptionId(value, allowedValues)
}

function isKnownOptionId(value: unknown, allowedValues: readonly string[]) {
  return typeof value === 'string' && allowedValues.includes(value)
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
