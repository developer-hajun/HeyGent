import { useMemo, useState, type CSSProperties } from 'react'
import {
  Background,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Bot,
  CheckCircle2,
  Circle,
  GitBranch,
  ListTree,
  MousePointer2,
  Plus,
  UserRound,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { HelpHint } from '@/components/ui/help-hint'
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
const WORK_NODE_WIDTH = 190
const CEO_NODE_WIDTH = 210
const NODE_GAP = 28
const MAP_SIDE_PADDING = 80
const FLOW_CANVAS_MIN_WIDTH = 820
const FLOW_CANVAS_HEIGHT = 520
const FLOW_ROOT_Y = 132
const FLOW_CHILD_Y = 292

type FlowNodeData = Record<string, unknown> & {
  assigneeName?: string
  issue?: IssueBoardIssue
  label?: string
  onConnectSelect?: () => void
  onOpen?: () => void
  onRequestAddAgent?: () => void
  primary?: boolean
  selectedForConnection?: boolean
  toolMode?: 'select' | 'connect'
}

type FlowNode = Node<FlowNodeData>
const FLOW_NODE_TYPES = {
  ceo: CeoFlowNode,
  work: WorkFlowNode,
  add: AddFlowNode,
}
const FLOW_EDGE_TYPES = {
  order: OrderLaneEdge,
}
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
  onReorderChildWork,
}: {
  assignees: BoardAssignee[]
  issues: IssueBoardIssue[]
  onAddRelation: (sourceId: string, targetId: string) => void
  onCreateChildWork: (parentId: string, input: CreateWorkInput) => void
  onCreateRootWork: (input: CreateWorkInput) => void
  onEnsureDefaultAgents: () => Promise<BoardAssignee[]>
  onOpenIssue: (issueId: string) => void
  onReorderChildWork: (parentId: string, workIds: string[]) => void
}) {
  const rootIssues = useMemo(
    () => sortFlowIssues(issues.filter((issue) => !issue.parentId)),
    [issues],
  )
  const [selectedRootId, setSelectedRootId] = useState<string | null>(rootIssues[0]?.id ?? null)
  const [draftTarget, setDraftTarget] = useState<DraftTarget | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftDescription, setDraftDescription] = useState('')
  const [toolMode, setToolMode] = useState<'select' | 'connect'>('select')
  const [connectionSourceId, setConnectionSourceId] = useState('')
  const [connectionPair, setConnectionPair] = useState<{
    firstId: string
    secondId: string
  } | null>(null)
  const [agentPickerOpen, setAgentPickerOpen] = useState(false)
  const [agentSeedPending, setAgentSeedPending] = useState(false)

  const selectedRoot =
    rootIssues.find((issue) => issue.id === selectedRootId) ?? rootIssues[0] ?? null
  const childIssues = useMemo(
    () =>
      sortFlowIssues(issues.filter((issue) => selectedRoot && issue.parentId === selectedRoot.id)),
    [issues, selectedRoot],
  )
  const validConnectionSourceId = childIssues.some((issue) => issue.id === connectionSourceId)
    ? connectionSourceId
    : ''
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

  const selectConnectIssue = (issueId: string) => {
    if (toolMode !== 'connect') return
    if (!validConnectionSourceId) {
      setConnectionSourceId(issueId)
      return
    }
    if (validConnectionSourceId === issueId) {
      setConnectionSourceId('')
      return
    }
    setConnectionPair({ firstId: validConnectionSourceId, secondId: issueId })
  }

  const firstConnectionIssue = connectionPair
    ? (childIssues.find((issue) => issue.id === connectionPair.firstId) ?? null)
    : null
  const secondConnectionIssue = connectionPair
    ? (childIssues.find((issue) => issue.id === connectionPair.secondId) ?? null)
    : null

  const closeConnectionChoice = () => {
    setConnectionPair(null)
    setConnectionSourceId('')
    setToolMode('select')
  }

  const confirmConnection = (sourceId: string, targetId: string) => {
    onAddRelation(sourceId, targetId)
    closeConnectionChoice()
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
              variant={toolMode === 'select' ? 'secondary' : 'ghost'}
              title="기본 선택"
              onClick={() => {
                setToolMode('select')
                setConnectionSourceId('')
              }}
            >
              <MousePointer2 className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              size="icon-sm"
              variant={toolMode === 'connect' ? 'secondary' : 'ghost'}
              title="실행 순서"
              disabled={childIssues.length < 2}
              onClick={() => {
                setToolMode((current) => (current === 'connect' ? 'select' : 'connect'))
                setConnectionSourceId('')
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

        <div className="border-border/70 flex h-12 items-center gap-2 border-b px-3">
          <ListTree className="text-muted-foreground h-4 w-4" />
          <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
            팀장 에이전트 작업
            <HelpHint label="작업 보드 도움말" iconClassName="h-3.5 w-3.5">
              <p className="text-foreground font-medium">작업 보드</p>
              <p>
                에이전트들의 <span className="text-foreground">할 일 목록</span>이에요.
              </p>
              <p>회사 화이트보드처럼 진행 상황을 한눈에 보여줍니다.</p>
              <ul className="text-muted-foreground mt-1 space-y-0.5 pl-3">
                <li>
                  · <span className="text-foreground">진행 중</span> — 작업 중
                </li>
                <li>
                  · <span className="text-foreground">대기</span> — 시작 전
                </li>
                <li>
                  · <span className="text-foreground">차단됨</span> — 다른 일이 먼저 끝나야 함
                </li>
                <li>
                  · <span className="text-foreground">검토</span> — 결과 확인 단계
                </li>
                <li>
                  · <span className="text-foreground">완료</span> — 끝난 일
                </li>
              </ul>
            </HelpHint>
          </span>
        </div>
        <div className="min-h-0 space-y-1 overflow-y-auto p-2">
          {rootIssues.map((issue, index) => (
            <button
              key={issue.id}
              type="button"
              onClick={() => setSelectedRootId(issue.id)}
              className={cn(
                'flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors',
                selectedRoot?.id === issue.id ? 'bg-accent text-foreground' : 'hover:bg-accent/50',
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
          ))}
          <button
            type="button"
            onClick={() =>
              openDraft({ agentName: '팀장 에이전트', assigneeAgentId: null, parentId: null })
            }
            className="border-primary/60 bg-primary/5 text-primary hover:bg-primary/10 mt-1 flex h-11 w-full items-center justify-center gap-1.5 rounded-md border border-dashed text-xs font-semibold transition-colors"
            aria-label="팀장 에이전트 작업 추가"
          >
            <Plus className="h-4 w-4" />
            작업 추가
          </button>
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
              setToolMode('select')
              setConnectionSourceId('')
            }}
            onOpenIssue={onOpenIssue}
            onReorderChildWork={onReorderChildWork}
            onSelectConnectIssue={selectConnectIssue}
            selectedConnectSourceId={validConnectionSourceId}
            toolMode={toolMode}
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
            placeholder="세부사항"
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
      {firstConnectionIssue && secondConnectionIssue && (
        <ConnectionChoiceDialog
          firstIssue={firstConnectionIssue}
          secondIssue={secondConnectionIssue}
          onCancel={closeConnectionChoice}
          onChooseFirstBeforeSecond={() =>
            confirmConnection(firstConnectionIssue.id, secondConnectionIssue.id)
          }
          onChooseSecondBeforeFirst={() =>
            confirmConnection(secondConnectionIssue.id, firstConnectionIssue.id)
          }
        />
      )}
    </div>
  )
}

function FixedMap({
  assignees,
  childIssues,
  rootIssue,
  onRequestAddAgent,
  onOpenIssue,
  onReorderChildWork,
  onSelectConnectIssue,
  selectedConnectSourceId,
  toolMode,
}: {
  assignees: BoardAssignee[]
  childIssues: IssueBoardIssue[]
  rootIssue: IssueBoardIssue
  onRequestAddAgent: () => void
  onOpenIssue: (issueId: string) => void
  onReorderChildWork: (parentId: string, workIds: string[]) => void
  onSelectConnectIssue: (issueId: string) => void
  selectedConnectSourceId: string
  toolMode: 'select' | 'connect'
}) {
  const childSlots = childIssues.length + 1
  const canvasWidth = flowCanvasWidth(childSlots)
  const childPositions = flowChildPositions(childSlots, canvasWidth)
  const addSlotX = childPositions[childIssues.length] ?? canvasWidth / 2
  const rootNodeId = `work:${rootIssue.id}`
  const nodes = useMemo<FlowNode[]>(
    () => [
      {
        id: 'ceo',
        type: 'ceo',
        position: { x: canvasWidth / 2 - CEO_NODE_WIDTH / 2, y: 42 },
        data: { label: '메인 에이전트' },
        style: { width: CEO_NODE_WIDTH },
        draggable: false,
      },
      {
        id: rootNodeId,
        type: 'work',
        position: { x: canvasWidth / 2 - WORK_NODE_WIDTH / 2, y: FLOW_ROOT_Y },
        data: {
          assigneeName: assigneeLabel(rootIssue.assigneeAgentId, assignees),
          issue: rootIssue,
          onOpen: () => onOpenIssue(rootIssue.id),
          primary: true,
          toolMode,
        },
        style: { width: WORK_NODE_WIDTH },
        draggable: false,
      },
      ...childIssues.map((issue, index) => ({
        id: `work:${issue.id}`,
        type: 'work',
        position: {
          x: (childPositions[index] ?? canvasWidth / 2) - WORK_NODE_WIDTH / 2,
          y: FLOW_CHILD_Y,
        },
        data: {
          assigneeName: assigneeLabel(issue.assigneeAgentId, assignees),
          issue,
          onConnectSelect: () => onSelectConnectIssue(issue.id),
          onOpen: () => onOpenIssue(issue.id),
          selectedForConnection: selectedConnectSourceId === issue.id,
          toolMode,
        },
        style: { width: WORK_NODE_WIDTH },
        draggable: true,
      })),
      {
        id: 'add-child',
        type: 'add',
        position: { x: addSlotX - WORK_NODE_WIDTH / 2, y: FLOW_CHILD_Y },
        data: { onRequestAddAgent },
        style: { width: WORK_NODE_WIDTH },
        draggable: false,
      },
    ],
    [
      addSlotX,
      assignees,
      canvasWidth,
      childIssues,
      childPositions,
      onOpenIssue,
      onRequestAddAgent,
      onSelectConnectIssue,
      rootIssue,
      rootNodeId,
      selectedConnectSourceId,
      toolMode,
    ],
  )
  const edges = useMemo<Edge[]>(
    () => [
      {
        id: 'ceo-root',
        source: 'ceo',
        target: rootNodeId,
        type: 'smoothstep',
        style: { strokeWidth: 2 },
      },
      ...childIssues.map((issue) => ({
        id: `${rootNodeId}:work:${issue.id}`,
        source: rootNodeId,
        target: `work:${issue.id}`,
        type: 'smoothstep',
        style: { strokeWidth: 2 },
      })),
      ...childIssues
        .flatMap((targetIssue) =>
          targetIssue.blockedBy
            .filter((sourceIssue) => childIssues.some((child) => child.id === sourceIssue.id))
            .map((sourceIssue) => ({ sourceIssue, targetIssue })),
        )
        .map(({ sourceIssue, targetIssue }, laneIndex) => {
          const sourceIndex = childIssues.findIndex((child) => child.id === sourceIssue.id)
          const targetIndex = childIssues.findIndex((child) => child.id === targetIssue.id)
          const movesRight = sourceIndex <= targetIndex
          return {
            id: `order:${sourceIssue.id}:${targetIssue.id}`,
            source: `work:${sourceIssue.id}`,
            sourceHandle: movesRight ? 'order-bottom-right-source' : 'order-bottom-left-source',
            target: `work:${targetIssue.id}`,
            targetHandle: movesRight ? 'order-bottom-left-target' : 'order-bottom-right-target',
            type: 'order',
            markerEnd: {
              color: 'currentColor',
              type: MarkerType.ArrowClosed,
              width: 12,
              height: 12,
            },
            className: 'text-primary',
            data: { laneIndex },
            style: { stroke: 'currentColor', strokeWidth: 2 },
          }
        }),
    ],
    [childIssues, rootNodeId],
  )
  const handleNodeDragStop = (_: React.MouseEvent, node: FlowNode) => {
    if (!node.id.startsWith('work:') || node.id === rootNodeId) return
    const issueId = node.id.slice('work:'.length)
    const currentIndex = childIssues.findIndex((issue) => issue.id === issueId)
    if (currentIndex < 0) return
    const centerX = node.position.x + WORK_NODE_WIDTH / 2
    const nextIndex = nearestSlotIndex(centerX, childPositions, childIssues.length)
    if (nextIndex === currentIndex) return
    const nextIds = childIssues.map((issue) => issue.id)
    const [moved] = nextIds.splice(currentIndex, 1)
    nextIds.splice(nextIndex, 0, moved)
    onReorderChildWork(rootIssue.id, nextIds)
  }
  return (
    <div
      className={cn(
        'relative h-full min-h-[420px] overflow-hidden',
        toolMode === 'connect' && 'cursor-crosshair',
      )}
      style={
        {
          '--xy-node-boxshadow-selected': 'none',
        } as CSSProperties
      }
    >
      <div className="absolute inset-0 overflow-x-auto overflow-y-hidden px-6 py-4">
        <div
          className="relative mx-auto h-full"
          style={{ width: canvasWidth, height: FLOW_CANVAS_HEIGHT }}
        >
          <ReactFlow
            className="[&_.react-flow__node]:!pointer-events-auto [&_.react-flow__node_*]:!pointer-events-auto"
            nodes={nodes}
            edges={edges}
            nodeTypes={FLOW_NODE_TYPES}
            edgeTypes={FLOW_EDGE_TYPES}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable={false}
            panOnDrag={false}
            paneClickDistance={1000}
            zoomOnScroll={false}
            zoomOnPinch={false}
            zoomOnDoubleClick={false}
            preventScrolling={false}
            defaultViewport={{ x: 0, y: 0, zoom: 1 }}
            minZoom={1}
            maxZoom={1}
            proOptions={{ hideAttribution: true }}
            onNodeDragStop={handleNodeDragStop}
          >
            <Background gap={24} size={1} />
          </ReactFlow>
        </div>
      </div>

      {toolMode === 'connect' && (
        <div className="bg-background/95 border-border text-foreground absolute top-3 left-3 z-10 rounded-md border px-3 py-2 text-xs shadow-sm">
          {selectedConnectSourceId
            ? '연결할 작업을 하나 더 선택하세요'
            : '연결할 작업 2개를 선택하세요'}
        </div>
      )}
    </div>
  )
}

function CeoCard({ label = '메인 에이전트' }: { label?: string }) {
  return (
    <div className="bg-background border-foreground/20 flex h-[60px] min-w-0 items-center gap-3 rounded-md border px-3 shadow-sm">
      <div className="bg-accent flex h-9 w-9 shrink-0 items-center justify-center rounded">
        <UserRound className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <div className="text-muted-foreground text-[11px] font-semibold tracking-widest uppercase">
          팀장 에이전트
        </div>
        <div className="truncate text-sm font-semibold">{label}</div>
      </div>
    </div>
  )
}

function CeoFlowNode({ data }: NodeProps<FlowNode>) {
  return (
    <>
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <CeoCard label={typeof data.label === 'string' ? data.label : '메인 에이전트'} />
    </>
  )
}

function WorkFlowNode({ data }: NodeProps<FlowNode>) {
  const issue = data.issue as IssueBoardIssue | undefined
  if (!issue) return null
  return (
    <>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <Handle type="source" position={Position.Bottom} className="opacity-0" />
      <Handle
        id="order-bottom-left-target"
        type="target"
        position={Position.Bottom}
        className="opacity-0"
        style={{ left: '32%' }}
      />
      <Handle
        id="order-bottom-right-target"
        type="target"
        position={Position.Bottom}
        className="opacity-0"
        style={{ left: '68%' }}
      />
      <Handle
        id="order-bottom-left-source"
        type="source"
        position={Position.Bottom}
        className="opacity-0"
        style={{ left: '32%' }}
      />
      <Handle
        id="order-bottom-right-source"
        type="source"
        position={Position.Bottom}
        className="opacity-0"
        style={{ left: '68%' }}
      />
      <WorkCard
        assigneeName={typeof data.assigneeName === 'string' ? data.assigneeName : '팀장 에이전트'}
        issue={issue}
        onConnectSelect={data.onConnectSelect as (() => void) | undefined}
        onOpen={(data.onOpen as () => void) ?? (() => undefined)}
        primary={data.primary === true}
        selectedForConnection={data.selectedForConnection === true}
        toolMode={data.toolMode === 'connect' ? 'connect' : 'select'}
      />
    </>
  )
}

function AddFlowNode({ data }: NodeProps<FlowNode>) {
  return (
    <div className="pointer-events-auto" style={{ width: WORK_NODE_WIDTH }}>
      <Handle type="target" position={Position.Top} className="opacity-0" />
      <AddAgentSlot
        onRequestAddAgent={(data.onRequestAddAgent as () => void) ?? (() => undefined)}
      />
    </div>
  )
}

function OrderLaneEdge({
  data,
  id,
  markerEnd,
  sourceX,
  sourceY,
  style,
  targetX,
  targetY,
}: EdgeProps) {
  const laneIndex = typeof data?.laneIndex === 'number' ? data.laneIndex : 0
  const laneY = Math.max(sourceY, targetY) + 30 + laneIndex * 18
  const direction = targetX >= sourceX ? 1 : -1
  const radius = Math.min(12, Math.max(4, Math.abs(targetX - sourceX) / 5))
  const path = [
    `M ${sourceX} ${sourceY}`,
    `L ${sourceX} ${laneY - radius}`,
    `Q ${sourceX} ${laneY} ${sourceX + direction * radius} ${laneY}`,
    `L ${targetX - direction * radius} ${laneY}`,
    `Q ${targetX} ${laneY} ${targetX} ${laneY - radius}`,
    `L ${targetX} ${targetY}`,
  ].join(' ')
  return (
    <path
      id={id}
      className="react-flow__edge-path stroke-primary"
      d={path}
      fill="none"
      markerEnd={markerEnd}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={style}
    />
  )
}

function WorkCard({
  assigneeName,
  issue,
  onConnectSelect,
  onOpen,
  primary = false,
  selectedForConnection = false,
  toolMode = 'select',
}: {
  assigneeName: string
  issue: IssueBoardIssue
  onConnectSelect?: () => void
  onOpen: () => void
  primary?: boolean
  selectedForConnection?: boolean
  toolMode?: 'select' | 'connect'
}) {
  const handleClick = () => {
    if (toolMode === 'connect' && onConnectSelect) {
      onConnectSelect()
      return
    }
    onOpen()
  }

  return (
    <div
      id={primary ? ROOT_NODE_ID : `${CHILD_NODE_PREFIX}${issue.id}`}
      className={cn(
        'bg-background border-border pointer-events-auto relative h-[96px] rounded-md border shadow-sm',
        primary && 'border-foreground/30',
        selectedForConnection && 'ring-primary ring-2',
      )}
    >
      <button
        type="button"
        onClick={handleClick}
        className={cn(
          'block h-full w-full px-3 py-2.5 text-left',
          toolMode === 'connect' && !primary && 'cursor-crosshair',
        )}
      >
        <div className="mb-1.5 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <StatusDot status={issue.status} />
          <span className="text-muted-foreground text-xs whitespace-nowrap">
            {issueBoardStatusLabel(issue.status)}
          </span>
          <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">
            {issue.identifier}
          </span>
        </div>
        <div
          className={cn(
            'line-clamp-2 min-h-9 text-sm leading-[18px] font-semibold',
            primary && 'text-[15px] leading-5',
          )}
        >
          {issue.title}
        </div>
        <div className="text-muted-foreground mt-1.5 flex min-w-0 items-center gap-1.5 text-xs">
          <Bot className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{assigneeName}</span>
        </div>
      </button>
    </div>
  )
}

function AddAgentSlot({ onRequestAddAgent }: { onRequestAddAgent: () => void }) {
  return (
    <button
      type="button"
      onClick={onRequestAddAgent}
      className="nodrag nopan border-primary bg-primary/10 text-primary hover:bg-primary/15 flex h-[96px] w-full flex-col items-center justify-center gap-1.5 rounded-md border-2 border-dashed shadow-sm transition-colors"
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

function ConnectionChoiceDialog({
  firstIssue,
  secondIssue,
  onCancel,
  onChooseFirstBeforeSecond,
  onChooseSecondBeforeFirst,
}: {
  firstIssue: IssueBoardIssue
  secondIssue: IssueBoardIssue
  onCancel: () => void
  onChooseFirstBeforeSecond: () => void
  onChooseSecondBeforeFirst: () => void
}) {
  return (
    <div className="bg-background/80 fixed inset-0 z-40 flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="border-border bg-background w-[360px] max-w-full rounded-md border p-4 shadow-xl">
        <div className="mb-1 text-sm font-semibold">작업 순서 선택</div>
        <p className="text-muted-foreground mb-4 text-xs leading-5">
          두 작업 중 먼저 끝나야 하는 작업을 고르세요. 선택한 작업에서 다른 작업으로 화살표가
          연결됩니다.
        </p>
        <div className="space-y-2">
          <Button
            type="button"
            variant="outline"
            className="h-auto w-full justify-start px-3 py-2 text-left"
            onClick={onChooseFirstBeforeSecond}
          >
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{firstIssue.title}</span>
              <span className="text-muted-foreground block truncate text-xs">
                이 작업 완료 후 {secondIssue.identifier} 진행
              </span>
            </span>
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-auto w-full justify-start px-3 py-2 text-left"
            onClick={onChooseSecondBeforeFirst}
          >
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{secondIssue.title}</span>
              <span className="text-muted-foreground block truncate text-xs">
                이 작업 완료 후 {firstIssue.identifier} 진행
              </span>
            </span>
          </Button>
        </div>
        <div className="mt-4 flex justify-end">
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            취소
          </Button>
        </div>
      </div>
    </div>
  )
}

function getDraftAssigneeName(target: DraftTarget, assignees: BoardAssignee[]) {
  if (target.agentName) return target.agentName
  if (target.parentId === null && target.assigneeAgentId === null) return '팀장 에이전트'
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

function flowCanvasWidth(totalSlots: number) {
  const slotWidth = totalSlots * WORK_NODE_WIDTH
  const gapWidth = Math.max(0, totalSlots - 1) * NODE_GAP
  return Math.max(FLOW_CANVAS_MIN_WIDTH, slotWidth + gapWidth + MAP_SIDE_PADDING * 2)
}

function flowChildPositions(totalSlots: number, canvasWidth: number) {
  const totalWidth = totalSlots * WORK_NODE_WIDTH + Math.max(0, totalSlots - 1) * NODE_GAP
  const start = canvasWidth / 2 - totalWidth / 2 + WORK_NODE_WIDTH / 2
  return Array.from(
    { length: totalSlots },
    (_, index) => start + index * (WORK_NODE_WIDTH + NODE_GAP),
  )
}

function nearestSlotIndex(x: number, positions: number[], itemCount: number) {
  const usablePositions = positions.slice(0, itemCount)
  if (usablePositions.length === 0) return 0
  let nearestIndex = 0
  let nearestDistance = Number.POSITIVE_INFINITY
  usablePositions.forEach((position, index) => {
    const distance = Math.abs(position - x)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestIndex = index
    }
  })
  return nearestIndex
}

function sortFlowIssues(issues: IssueBoardIssue[]) {
  return [...issues].sort((left, right) => {
    const leftOrder = left.flowOrder ?? Number.MAX_SAFE_INTEGER
    const rightOrder = right.flowOrder ?? Number.MAX_SAFE_INTEGER
    if (leftOrder !== rightOrder) return leftOrder - rightOrder
    return new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime()
  })
}
