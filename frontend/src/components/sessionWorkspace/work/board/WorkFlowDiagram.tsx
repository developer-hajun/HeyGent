import { useMemo, useState } from 'react'
import { Bot, CheckCircle2, Circle, GitBranch, ListTree, Plus, UserRound, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/components/ui/utils'
import type { IssueBoardIssue } from '../model/issueBoardModel'
import { issueBoardStatusLabel } from '../model/issueBoardModel'
import type { BoardAssignee } from './issueBoardPanelTypes'
import { assigneeLabel, formatRelativeTime } from './issueBoardPanelUtils'

type CreateWorkInput = {
  assigneeAgentId: string | null
  description: string
  title: string
}

type DraftTarget = {
  agentName?: string
  assigneeAgentId: string | null
  parentId: string | null
}

type AgentChoice = {
  assigneeAgentId: string | null
  defaultTitle: string
  id: string
  name: string
  provided?: boolean
  templateKey?: string
}

const ROOT_NODE_ID = 'flow-root-task'
const CHILD_NODE_PREFIX = 'flow-child-'
const DEFAULT_AGENT_CHOICES: AgentChoice[] = [
  {
    id: 'provided-default',
    name: '기본 에이전트',
    defaultTitle: '보조 작업',
    assigneeAgentId: null,
    provided: true,
    templateKey: 'default',
  },
  {
    id: 'provided-coder',
    name: '개발 에이전트',
    defaultTitle: '개발 작업',
    assigneeAgentId: null,
    provided: true,
    templateKey: 'coder',
  },
  {
    id: 'provided-qa',
    name: 'QA 에이전트',
    defaultTitle: '검증 작업',
    assigneeAgentId: null,
    provided: true,
    templateKey: 'qa',
  },
  {
    id: 'provided-ux-designer',
    name: 'UX 디자이너',
    defaultTitle: 'UX 검토',
    assigneeAgentId: null,
    provided: true,
    templateKey: 'ux_designer',
  },
  {
    id: 'provided-security',
    name: '보안 에이전트',
    defaultTitle: '보안 검토',
    assigneeAgentId: null,
    provided: true,
    templateKey: 'security_engineer',
  },
]

export function WorkFlowDiagram({
  assignees,
  issues,
  onAddRelation,
  onCreateChildWork,
  onCreateRootWork,
  onEnsureDefaultAgents,
  onOpenIssue,
  onReorderRootWork,
}: {
  assignees: BoardAssignee[]
  issues: IssueBoardIssue[]
  onAddRelation: (sourceId: string, targetId: string) => void
  onCreateChildWork: (parentId: string, input: CreateWorkInput) => void
  onCreateRootWork: (input: CreateWorkInput) => void
  onEnsureDefaultAgents: () => Promise<BoardAssignee[]>
  onOpenIssue: (issueId: string) => void
  onReorderRootWork: (workIds: string[]) => void
}) {
  const rootIssues = useMemo(
    () => sortFlowIssues(issues.filter((issue) => !issue.parentId)),
    [issues],
  )
  const [selectedRootId, setSelectedRootId] = useState<string | null>(rootIssues[0]?.id ?? null)
  const [draftTarget, setDraftTarget] = useState<DraftTarget | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftDescription, setDraftDescription] = useState('')
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [agentPickerOpen, setAgentPickerOpen] = useState(false)
  const [orderPanelOpen, setOrderPanelOpen] = useState(false)
  const [agentSeedPending, setAgentSeedPending] = useState(false)

  const selectedRoot =
    rootIssues.find((issue) => issue.id === selectedRootId) ?? rootIssues[0] ?? null
  const childIssues = useMemo(
    () =>
      sortFlowIssues(issues.filter((issue) => selectedRoot && issue.parentId === selectedRoot.id)),
    [issues, selectedRoot],
  )
  const validSourceId = childIssues.some((issue) => issue.id === sourceId) ? sourceId : ''
  const validTargetId = childIssues.some((issue) => issue.id === targetId) ? targetId : ''
  const agentChoices = useMemo<AgentChoice[]>(
    () => [
      ...assignees
        .filter((assignee) => assignee.id !== 'CEO')
        .map((assignee) => ({
          id: assignee.id,
          name: assignee.name,
          defaultTitle: `${assignee.name} 작업`,
          assigneeAgentId: assignee.id,
          templateKey: assignee.templateKey,
        })),
      ...DEFAULT_AGENT_CHOICES.filter(
        (choice) => !assignees.some((assignee) => assignee.templateKey === choice.templateKey),
      ),
    ],
    [assignees],
  )

  const openDraft = (target: DraftTarget, title = '') => {
    setDraftTarget(target)
    setDraftTitle(title)
    setDraftDescription('')
  }

  const openAgentDraft = async (agent: AgentChoice) => {
    if (!selectedRoot) return
    if (agent.provided && agent.templateKey) {
      setAgentSeedPending(true)
      try {
        const nextAssignees = await onEnsureDefaultAgents()
        const matchedAssignee =
          nextAssignees.find((assignee) => assignee.templateKey === agent.templateKey) ?? null
        openDraft(
          {
            agentName: matchedAssignee?.name ?? agent.name,
            assigneeAgentId: matchedAssignee?.id ?? null,
            parentId: selectedRoot.id,
          },
          agent.defaultTitle,
        )
        setAgentPickerOpen(false)
      } finally {
        setAgentSeedPending(false)
      }
      return
    }
    openDraft(
      {
        agentName: agent.name,
        assigneeAgentId: agent.assigneeAgentId,
        parentId: selectedRoot.id,
      },
      agent.defaultTitle,
    )
    setAgentPickerOpen(false)
  }

  const submitDraft = () => {
    const title = draftTitle.trim()
    if (!title || draftTarget === null) return
    const description = draftDescription.trim() || title
    const payload = {
      assigneeAgentId: draftTarget.assigneeAgentId,
      title,
      description,
    }
    if (draftTarget.parentId) {
      onCreateChildWork(draftTarget.parentId, payload)
    } else {
      onCreateRootWork(payload)
    }
    setDraftTarget(null)
    setDraftTitle('')
    setDraftDescription('')
  }

  const moveRootIssue = (issueId: string, direction: -1 | 1) => {
    const currentIndex = rootIssues.findIndex((issue) => issue.id === issueId)
    const nextIndex = currentIndex + direction
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= rootIssues.length) return
    const next = [...rootIssues]
    const [item] = next.splice(currentIndex, 1)
    next.splice(nextIndex, 0, item)
    onReorderRootWork(next.map((issue) => issue.id))
  }

  const connectOrder = () => {
    if (!validSourceId || !validTargetId || validSourceId === validTargetId) return
    onAddRelation(validSourceId, validTargetId)
    setSourceId('')
    setTargetId('')
  }

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[12.5rem_minmax(0,1fr)] overflow-hidden">
      <aside className="border-border/70 bg-muted/10 relative min-h-0 border-r">
        <div className="border-border/70 border-b px-3 py-2">
          <div className="text-muted-foreground mb-1.5 text-[10px] font-semibold tracking-widest uppercase">
            도구
          </div>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              size="icon-sm"
              variant="ghost"
              title="실행 순서"
              disabled={childIssues.length < 2}
              onClick={() => {
                setOrderPanelOpen((current) => !current)
                setAgentPickerOpen(false)
              }}
            >
              <GitBranch className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {agentPickerOpen && (
          <AgentPicker
            agents={agentChoices}
            disabled={agentSeedPending}
            onChoose={openAgentDraft}
            onClose={() => setAgentPickerOpen(false)}
          />
        )}

        {orderPanelOpen && (
          <OrderToolPanel
            childIssues={childIssues}
            sourceId={validSourceId}
            targetId={validTargetId}
            onConnect={connectOrder}
            onSourceChange={setSourceId}
            onTargetChange={setTargetId}
          />
        )}

        <div className="border-border/70 flex h-12 items-center gap-2 border-b px-3">
          <ListTree className="text-muted-foreground h-4 w-4" />
          <span className="text-sm font-semibold">CEO 작업</span>
        </div>
        <div className="min-h-0 space-y-1 overflow-y-auto p-2">
          {rootIssues.length === 0 ? (
            <button
              type="button"
              onClick={() => openDraft({ agentName: 'CEO', assigneeAgentId: null, parentId: null })}
              className="border-primary/60 bg-primary/5 text-primary hover:bg-primary/10 flex h-20 w-full flex-col items-center justify-center gap-1 rounded-md border border-dashed text-xs font-semibold transition-colors"
              aria-label="CEO 작업 추가"
            >
              <Plus className="h-5 w-5" />
              작업 추가
            </button>
          ) : (
            rootIssues.map((issue, index) => (
              <button
                key={issue.id}
                type="button"
                onClick={() => setSelectedRootId(issue.id)}
                className={cn(
                  'flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors',
                  selectedRoot?.id === issue.id
                    ? 'bg-accent text-foreground'
                    : 'hover:bg-accent/50',
                )}
              >
                <StatusDot status={issue.status} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium">{issue.title}</span>
                  <span className="text-muted-foreground mt-0.5 block truncate text-xs">
                    {issue.identifier} · {formatRelativeTime(issue.updatedAt)}
                  </span>
                </span>
                <span className="text-muted-foreground text-xs tabular-nums">{index + 1}</span>
              </button>
            ))
          )}
        </div>
      </aside>

      <main className="bg-background relative min-h-0 overflow-hidden">
        {selectedRoot ? (
          <FixedMap
            assignees={assignees}
            childIssues={childIssues}
            rootIssue={selectedRoot}
            onRequestAddAgent={() => {
              setAgentPickerOpen(true)
              setOrderPanelOpen(false)
            }}
            onMoveRoot={moveRootIssue}
            onOpenIssue={onOpenIssue}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="border-border text-muted-foreground flex h-32 w-64 items-center justify-center rounded-md border border-dashed text-sm">
              작업 생성이 필요합니다
            </div>
          </div>
        )}
      </main>

      {draftTarget && (
        <div className="border-border bg-background fixed right-6 bottom-6 z-50 w-[340px] max-w-[calc(100vw-3rem)] rounded-md border p-3 shadow-xl">
          <div className="mb-3 flex items-center gap-2">
            <Bot className="text-muted-foreground h-4 w-4" />
            <span className="min-w-0 flex-1 truncate text-sm font-medium">
              {getDraftAssigneeName(draftTarget, assignees)}
            </span>
            <button
              type="button"
              onClick={() => setDraftTarget(null)}
              className="hover:bg-accent/50 flex h-7 w-7 items-center justify-center rounded"
              aria-label="닫기"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <input
            value={draftTitle}
            onChange={(event) => setDraftTitle(event.target.value)}
            placeholder="작업 제목"
            className="border-input bg-background focus-visible:ring-ring/40 h-9 w-full rounded-md border px-2 text-sm outline-none focus-visible:ring-2"
          />
          <Textarea
            value={draftDescription}
            onChange={(event) => setDraftDescription(event.target.value)}
            placeholder="코멘트"
            className="mt-2 min-h-20 resize-y"
          />
          <div className="mt-3 flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setDraftTarget(null)}>
              취소
            </Button>
            <Button type="button" size="sm" onClick={submitDraft} disabled={!draftTitle.trim()}>
              추가
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function FixedMap({
  assignees,
  childIssues,
  rootIssue,
  onRequestAddAgent,
  onMoveRoot,
  onOpenIssue,
}: {
  assignees: BoardAssignee[]
  childIssues: IssueBoardIssue[]
  rootIssue: IssueBoardIssue
  onRequestAddAgent: () => void
  onMoveRoot: (issueId: string, direction: -1 | 1) => void
  onOpenIssue: (issueId: string) => void
}) {
  const childSlots = childIssues.length + 1
  const addSlotX = childXPercent(childIssues.length, childSlots)
  return (
    <div className="relative h-full min-h-[380px] overflow-hidden px-5 py-4">
      <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
        <line x1="50%" y1="78" x2="50%" y2="144" className="stroke-border" strokeWidth="2" />
        {childIssues.map((issue, index) => {
          const x = childXPercent(index, childSlots)
          return (
            <g key={issue.id}>
              <line
                x1="50%"
                y1="236"
                x2={`${x}%`}
                y2="292"
                className="stroke-border"
                strokeWidth="2"
              />
              {issue.blockedBy
                .filter((blockedBy) => childIssues.some((child) => child.id === blockedBy.id))
                .map((blockedBy) => {
                  const sourceIndex = childIssues.findIndex((child) => child.id === blockedBy.id)
                  const sourceX = childXPercent(sourceIndex, childSlots)
                  return (
                    <line
                      key={`${blockedBy.id}:${issue.id}`}
                      x1={`${sourceX}%`}
                      y1="346"
                      x2={`${x}%`}
                      y2="346"
                      className="stroke-primary"
                      strokeWidth="2"
                    />
                  )
                })}
            </g>
          )
        })}
        <line
          x1="50%"
          y1="236"
          x2={`${addSlotX}%`}
          y2="292"
          className="stroke-primary"
          strokeDasharray="5 5"
          strokeWidth="2"
        />
      </svg>

      <div className="absolute top-4 left-1/2 w-[168px] -translate-x-1/2">
        <CeoCard />
      </div>
      <div className="absolute top-[144px] left-1/2 w-[210px] -translate-x-1/2">
        <WorkCard
          assigneeName={assigneeLabel(rootIssue.assigneeAgentId, assignees)}
          issue={rootIssue}
          primary
          onMoveLeft={() => onMoveRoot(rootIssue.id, -1)}
          onMoveRight={() => onMoveRoot(rootIssue.id, 1)}
          onOpen={() => onOpenIssue(rootIssue.id)}
        />
      </div>

      <div
        className="absolute top-[292px] right-8 left-8 grid items-start gap-2.5"
        style={{ gridTemplateColumns: `repeat(${childSlots}, minmax(0, 1fr))` }}
      >
        {childIssues.map((issue) => (
          <WorkCard
            key={issue.id}
            assigneeName={assigneeLabel(issue.assigneeAgentId, assignees)}
            issue={issue}
            onOpen={() => onOpenIssue(issue.id)}
          />
        ))}
        <AddAgentSlot onRequestAddAgent={onRequestAddAgent} />
      </div>
    </div>
  )
}

function CeoCard() {
  return (
    <div className="bg-background border-foreground/20 flex h-[52px] items-center gap-2 rounded-md border px-2.5 shadow-sm">
      <div className="bg-accent flex h-8 w-8 shrink-0 items-center justify-center rounded">
        <UserRound className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
          CEO
        </div>
        <div className="truncate text-[13px] font-semibold">메인 에이전트</div>
      </div>
    </div>
  )
}

function WorkCard({
  assigneeName,
  issue,
  onMoveLeft,
  onMoveRight,
  onOpen,
  primary = false,
}: {
  assigneeName: string
  issue: IssueBoardIssue
  onMoveLeft?: () => void
  onMoveRight?: () => void
  onOpen: () => void
  primary?: boolean
}) {
  return (
    <div
      id={primary ? ROOT_NODE_ID : `${CHILD_NODE_PREFIX}${issue.id}`}
      className={cn(
        'bg-background border-border rounded-md border shadow-sm',
        primary && 'border-foreground/30',
      )}
    >
      <button type="button" onClick={onOpen} className="block w-full px-2 py-1.5 text-left">
        <div className="mb-1 flex items-center gap-1.5">
          <StatusDot status={issue.status} />
          <span className="text-muted-foreground truncate text-xs">
            {issueBoardStatusLabel(issue.status)}
          </span>
          <span className="text-muted-foreground ml-auto font-mono text-xs">
            {issue.identifier}
          </span>
        </div>
        <div
          className={cn(
            'line-clamp-2 min-h-7 text-xs leading-[15px] font-semibold',
            primary && 'text-[13px]',
          )}
        >
          {issue.title}
        </div>
        <div className="text-muted-foreground mt-1 flex min-w-0 items-center gap-1.5 text-xs">
          <Bot className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{assigneeName}</span>
        </div>
      </button>
      {primary && (
        <div className="border-border/70 flex border-t">
          <button
            type="button"
            onClick={onMoveLeft}
            className="hover:bg-accent/50 h-6 flex-1 text-xs"
          >
            왼쪽
          </button>
          <button
            type="button"
            onClick={onMoveRight}
            className="hover:bg-accent/50 h-6 flex-1 border-l text-xs"
          >
            오른쪽
          </button>
        </div>
      )}
    </div>
  )
}

function AddAgentSlot({ onRequestAddAgent }: { onRequestAddAgent: () => void }) {
  return (
    <button
      type="button"
      onClick={onRequestAddAgent}
      className="border-primary bg-primary/10 text-primary hover:bg-primary/15 flex min-h-[76px] flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed shadow-sm transition-colors"
      aria-label="하위 에이전트 작업 추가"
    >
      <span className="bg-primary text-primary-foreground flex h-7 w-7 items-center justify-center rounded">
        <Plus className="h-4 w-4" />
      </span>
      <span className="text-xs font-semibold">추가</span>
    </button>
  )
}

function AgentPicker({
  agents,
  disabled,
  onChoose,
  onClose,
}: {
  agents: AgentChoice[]
  disabled: boolean
  onChoose: (agent: AgentChoice) => void | Promise<void>
  onClose: () => void
}) {
  const assignedAgents = agents.filter((agent) => !agent.provided)
  const providedAgents = agents.filter((agent) => agent.provided)

  return (
    <div className="border-border bg-background absolute top-14 left-3 z-30 w-60 rounded-md border p-2 shadow-xl">
      <div className="mb-1 flex items-center gap-2 px-1">
        <Bot className="text-muted-foreground h-4 w-4" />
        <span className="flex-1 text-sm font-semibold">에이전트 선택</span>
        <button
          type="button"
          onClick={onClose}
          className="hover:bg-accent/50 flex h-7 w-7 items-center justify-center rounded"
          aria-label="닫기"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {assignedAgents.length > 0 && (
        <AgentChoiceGroup
          disabled={disabled}
          label="연결됨"
          agents={assignedAgents}
          onChoose={onChoose}
        />
      )}
      <AgentChoiceGroup
        disabled={disabled}
        label="기본 제공"
        agents={providedAgents}
        onChoose={onChoose}
      />
    </div>
  )
}

function AgentChoiceGroup({
  agents,
  disabled,
  label,
  onChoose,
}: {
  agents: AgentChoice[]
  disabled: boolean
  label: string
  onChoose: (agent: AgentChoice) => void | Promise<void>
}) {
  return (
    <div className="mt-2">
      <div className="text-muted-foreground px-1 pb-1 text-[10px] font-semibold tracking-widest uppercase">
        {label}
      </div>
      <div className="space-y-0.5">
        {agents.map((agent) => (
          <button
            key={agent.id}
            type="button"
            onClick={() => onChoose(agent)}
            disabled={disabled}
            className="hover:bg-accent/50 flex h-8 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition-colors"
          >
            <Bot className="h-4 w-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate">{agent.name}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function OrderToolPanel({
  childIssues,
  sourceId,
  targetId,
  onConnect,
  onSourceChange,
  onTargetChange,
}: {
  childIssues: IssueBoardIssue[]
  sourceId: string
  targetId: string
  onConnect: () => void
  onSourceChange: (issueId: string) => void
  onTargetChange: (issueId: string) => void
}) {
  return (
    <div className="border-border bg-background absolute top-14 left-3 z-30 w-64 rounded-md border p-3 shadow-xl">
      <div className="text-muted-foreground mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-widest uppercase">
        <GitBranch className="h-3.5 w-3.5" />
        실행 순서
      </div>
      <select
        value={sourceId}
        onChange={(event) => onSourceChange(event.target.value)}
        className="bg-background border-border mb-2 h-8 w-full rounded-md border px-2 text-xs"
      >
        <option value="">먼저 실행</option>
        {childIssues.map((issue) => (
          <option key={issue.id} value={issue.id}>
            {issue.title}
          </option>
        ))}
      </select>
      <select
        value={targetId}
        onChange={(event) => onTargetChange(event.target.value)}
        className="bg-background border-border mb-2 h-8 w-full rounded-md border px-2 text-xs"
      >
        <option value="">다음 실행</option>
        {childIssues.map((issue) => (
          <option key={issue.id} value={issue.id}>
            {issue.title}
          </option>
        ))}
      </select>
      <Button
        type="button"
        size="sm"
        className="w-full"
        disabled={!sourceId || !targetId || sourceId === targetId}
        onClick={onConnect}
      >
        연결
      </Button>
    </div>
  )
}

function getDraftAssigneeName(target: DraftTarget, assignees: BoardAssignee[]) {
  if (target.agentName) return target.agentName
  if (target.parentId === null && target.assigneeAgentId === null) return 'CEO'
  return assigneeLabel(target.assigneeAgentId, assignees)
}

function StatusDot({ status }: { status: IssueBoardIssue['status'] }) {
  if (status === 'done') {
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
  }
  return (
    <Circle
      className={cn(
        'h-4 w-4 shrink-0',
        status === 'blocked' && 'text-amber-600',
        status === 'in_progress' && 'text-blue-600',
        status !== 'blocked' && status !== 'in_progress' && 'text-muted-foreground',
      )}
    />
  )
}

function childXPercent(index: number, totalSlots: number) {
  if (totalSlots <= 1) return 50
  return 10 + (index * 80) / Math.max(1, totalSlots - 1)
}

function sortFlowIssues(issues: IssueBoardIssue[]) {
  return [...issues].sort((left, right) => {
    const leftOrder = left.flowOrder ?? Number.MAX_SAFE_INTEGER
    const rightOrder = right.flowOrder ?? Number.MAX_SAFE_INTEGER
    if (leftOrder !== rightOrder) return leftOrder - rightOrder
    return new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime()
  })
}
