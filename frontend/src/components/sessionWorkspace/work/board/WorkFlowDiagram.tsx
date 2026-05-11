import { useMemo, useState, type DragEvent } from 'react'
import {
  Bot,
  CheckCircle2,
  ChevronRight,
  Circle,
  GitBranch,
  ListTree,
  Plus,
  UserRound,
  X,
} from 'lucide-react'
import { useNavigate } from 'react-router'
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
  assigneeAgentId: string | null
  parentId: string | null
}

const ROOT_NODE_ID = 'flow-root-task'
const CHILD_NODE_PREFIX = 'flow-child-'

export function WorkFlowDiagram({
  assignees,
  issues,
  onAddRelation,
  onCreateChildWork,
  onCreateRootWork,
  onOpenIssue,
  onReorderRootWork,
  sessionId,
}: {
  assignees: BoardAssignee[]
  issues: IssueBoardIssue[]
  onAddRelation: (sourceId: string, targetId: string) => void
  onCreateChildWork: (parentId: string, input: CreateWorkInput) => void
  onCreateRootWork: (input: CreateWorkInput) => void
  onOpenIssue: (issueId: string) => void
  onReorderRootWork: (workIds: string[]) => void
  sessionId: string
}) {
  const navigate = useNavigate()
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

  const selectedRoot =
    rootIssues.find((issue) => issue.id === selectedRootId) ?? rootIssues[0] ?? null
  const childIssues = useMemo(
    () =>
      sortFlowIssues(issues.filter((issue) => selectedRoot && issue.parentId === selectedRoot.id)),
    [issues, selectedRoot],
  )
  const validSourceId = childIssues.some((issue) => issue.id === sourceId) ? sourceId : ''
  const validTargetId = childIssues.some((issue) => issue.id === targetId) ? targetId : ''

  const openDraft = (target: DraftTarget) => {
    setDraftTarget(target)
    setDraftTitle('')
    setDraftDescription('')
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
    <div className="grid min-h-0 flex-1 grid-cols-[14rem_minmax(0,1fr)_15rem] overflow-hidden">
      <aside className="border-border/70 bg-muted/10 min-h-0 border-r">
        <div className="border-border/70 flex h-12 items-center gap-2 border-b px-3">
          <ListTree className="text-muted-foreground h-4 w-4" />
          <span className="text-sm font-semibold">CEO 작업</span>
          <Button
            type="button"
            size="icon-sm"
            variant="ghost"
            className="ml-auto"
            onClick={() => openDraft({ assigneeAgentId: null, parentId: null })}
            aria-label="CEO 작업 추가"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="min-h-0 space-y-1 overflow-y-auto p-2">
          {rootIssues.length === 0 ? (
            <button
              type="button"
              onClick={() => openDraft({ assigneeAgentId: null, parentId: null })}
              className="text-muted-foreground hover:bg-accent/50 flex h-20 w-full items-center justify-center rounded-md border border-dashed text-sm"
            >
              <Plus className="mr-1.5 h-4 w-4" />
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
            onDropAgent={(assigneeAgentId) =>
              openDraft({ assigneeAgentId, parentId: selectedRoot.id })
            }
            onMoveRoot={moveRootIssue}
            onOpenIssue={onOpenIssue}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <button
              type="button"
              onClick={() => openDraft({ assigneeAgentId: null, parentId: null })}
              className="border-border hover:bg-accent/40 flex h-32 w-64 items-center justify-center gap-2 rounded-md border border-dashed text-sm"
            >
              <Plus className="h-4 w-4" />
              작업 추가
            </button>
          </div>
        )}
      </main>

      <aside className="border-border/70 bg-muted/10 min-h-0 border-l">
        <div className="border-border/70 flex h-12 items-center gap-2 border-b px-3">
          <Bot className="text-muted-foreground h-4 w-4" />
          <span className="text-sm font-semibold">에이전트</span>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="ml-auto h-8 px-2"
            onClick={() => navigate(`/session/${sessionId}/workspace/sub-agents`)}
          >
            추가
          </Button>
        </div>
        <div className="space-y-3 p-2">
          <div className="space-y-1">
            {assignees
              .filter((assignee) => assignee.id !== 'CEO')
              .map((assignee) => (
                <button
                  key={assignee.id}
                  type="button"
                  draggable
                  onDragStart={(event) => {
                    event.dataTransfer.effectAllowed = 'copy'
                    event.dataTransfer.setData('application/heygent-agent', assignee.id)
                  }}
                  onClick={() =>
                    selectedRoot &&
                    openDraft({ assigneeAgentId: assignee.id, parentId: selectedRoot.id })
                  }
                  className="hover:bg-accent/50 flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm transition-colors"
                >
                  <Bot className="h-4 w-4 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">{assignee.name}</span>
                  <ChevronRight className="text-muted-foreground h-4 w-4" />
                </button>
              ))}
            {assignees.filter((assignee) => assignee.id !== 'CEO').length === 0 && (
              <button
                type="button"
                onClick={() => navigate(`/session/${sessionId}/workspace/sub-agents`)}
                className="text-muted-foreground hover:bg-accent/50 flex h-16 w-full items-center justify-center rounded-md border border-dashed text-sm"
              >
                <Plus className="mr-1.5 h-4 w-4" />
                에이전트 추가
              </button>
            )}
          </div>
          <div className="border-border/70 border-t pt-3">
            <div className="text-muted-foreground mb-2 flex items-center gap-1.5 text-xs font-semibold tracking-widest uppercase">
              <GitBranch className="h-3.5 w-3.5" />
              실행 순서
            </div>
            <select
              value={validSourceId}
              onChange={(event) => setSourceId(event.target.value)}
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
              value={validTargetId}
              onChange={(event) => setTargetId(event.target.value)}
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
              disabled={!validSourceId || !validTargetId || validSourceId === validTargetId}
              onClick={connectOrder}
            >
              연결
            </Button>
          </div>
        </div>
      </aside>

      {draftTarget && (
        <div className="border-border bg-background fixed right-6 bottom-6 z-50 w-[340px] max-w-[calc(100vw-3rem)] rounded-md border p-3 shadow-xl">
          <div className="mb-3 flex items-center gap-2">
            <Bot className="text-muted-foreground h-4 w-4" />
            <span className="min-w-0 flex-1 truncate text-sm font-medium">
              {assigneeLabel(draftTarget.assigneeAgentId, assignees)}
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
  onDropAgent,
  onMoveRoot,
  onOpenIssue,
}: {
  assignees: BoardAssignee[]
  childIssues: IssueBoardIssue[]
  rootIssue: IssueBoardIssue
  onDropAgent: (assigneeAgentId: string | null) => void
  onMoveRoot: (issueId: string, direction: -1 | 1) => void
  onOpenIssue: (issueId: string) => void
}) {
  const childSlots = childIssues.length + 1
  return (
    <div className="relative h-full min-h-[420px] overflow-hidden px-5 py-4">
      <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
        <line x1="50%" y1="86" x2="50%" y2="166" className="stroke-border" strokeWidth="2" />
        {childIssues.map((issue, index) => {
          const x = childXPercent(index, childSlots)
          return (
            <g key={issue.id}>
              <line
                x1="50%"
                y1="274"
                x2={`${x}%`}
                y2="334"
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
                      y1="402"
                      x2={`${x}%`}
                      y2="402"
                      className="stroke-primary"
                      strokeWidth="2"
                    />
                  )
                })}
            </g>
          )
        })}
      </svg>

      <div className="absolute top-4 left-1/2 w-[200px] -translate-x-1/2">
        <CeoCard />
      </div>
      <div className="absolute top-[166px] left-1/2 w-[260px] -translate-x-1/2">
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
        className="absolute right-4 bottom-5 left-4 grid items-start gap-3"
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
        <DropAddSlot onDropAgent={onDropAgent} />
      </div>
    </div>
  )
}

function CeoCard() {
  return (
    <div className="bg-background border-foreground/20 flex h-[68px] items-center gap-2 rounded-md border px-3 shadow-sm">
      <div className="bg-accent flex h-9 w-9 shrink-0 items-center justify-center rounded">
        <UserRound className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
          CEO
        </div>
        <div className="truncate text-sm font-semibold">메인 에이전트</div>
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
      <button type="button" onClick={onOpen} className="block w-full px-2.5 py-2.5 text-left">
        <div className="mb-1.5 flex items-center gap-1.5">
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
            'line-clamp-2 min-h-9 text-[13px] leading-[18px] font-semibold',
            primary && 'text-sm',
          )}
        >
          {issue.title}
        </div>
        <div className="text-muted-foreground mt-2 flex min-w-0 items-center gap-1.5 text-xs">
          <Bot className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{assigneeName}</span>
        </div>
      </button>
      {primary && (
        <div className="border-border/70 flex border-t">
          <button
            type="button"
            onClick={onMoveLeft}
            className="hover:bg-accent/50 h-7 flex-1 text-xs"
          >
            왼쪽
          </button>
          <button
            type="button"
            onClick={onMoveRight}
            className="hover:bg-accent/50 h-7 flex-1 border-l text-xs"
          >
            오른쪽
          </button>
        </div>
      )}
    </div>
  )
}

function DropAddSlot({ onDropAgent }: { onDropAgent: (assigneeAgentId: string | null) => void }) {
  const [active, setActive] = useState(false)
  return (
    <button
      type="button"
      onClick={() => onDropAgent(null)}
      onDragOver={(event) => {
        event.preventDefault()
        event.dataTransfer.dropEffect = 'copy'
        setActive(true)
      }}
      onDragLeave={() => setActive(false)}
      onDrop={(event: DragEvent<HTMLButtonElement>) => {
        event.preventDefault()
        setActive(false)
        const agentId = event.dataTransfer.getData('application/heygent-agent')
        onDropAgent(agentId === '' || agentId === 'CEO' ? null : agentId)
      }}
      className={cn(
        'border-border text-muted-foreground hover:bg-accent/50 flex min-h-[112px] items-center justify-center rounded-md border border-dashed transition-colors',
        active && 'bg-accent/60 text-foreground',
      )}
    >
      <Plus className="h-7 w-7" />
    </button>
  )
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
