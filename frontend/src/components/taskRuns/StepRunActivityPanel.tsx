import {
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  RotateCcw,
  ShieldCheck,
  X,
  XCircle,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { ChatMessageView } from '@/types/aiChat'
import type { RawApproval, RawStepRun, RawTaskRun, TaskRunStatusTone } from '@/types/taskRuns'
import {
  toActivityItemView,
  toTaskRunStatusText,
  toTaskRunStatusTone,
  toTaskRunSummaryView,
} from '@/utils/taskRunStatusView'

const EMPTY_MESSAGES: never[] = []

type StepRunActivityPanelProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string | undefined) => void
}

export function StepRunActivityPanel({
  open,
  onOpenChange,
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
}: StepRunActivityPanelProps) {
  const isDesktop = useIsDesktopViewport()

  return (
    <>
      {open && isDesktop && (
        <aside className="border-border bg-popover hidden w-96 shrink-0 flex-col border-l lg:flex">
          <PanelBody
            sessionId={sessionId}
            selectedTaskRunId={selectedTaskRunId}
            onSelectTaskRun={onSelectTaskRun}
            onClose={() => onOpenChange(false)}
          />
        </aside>
      )}
      {!isDesktop && (
        <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
          <DrawerContent className="bg-popover max-h-[86vh] p-0">
            <DrawerHeader className="sr-only">
              <DrawerTitle>진행 상황</DrawerTitle>
              <DrawerDescription>현재 답변의 진행 단계와 세부 기록입니다.</DrawerDescription>
            </DrawerHeader>
            <PanelBody
              sessionId={sessionId}
              selectedTaskRunId={selectedTaskRunId}
              onSelectTaskRun={onSelectTaskRun}
              onClose={() => onOpenChange(false)}
            />
          </DrawerContent>
        </Drawer>
      )}
    </>
  )
}

function PanelBody({
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
  onClose,
}: {
  sessionId: string
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string | undefined) => void
  onClose: () => void
}) {
  const messages = useChatStore((state) =>
    sessionId === '' ? EMPTY_MESSAGES : (state.messagesBySessionId[sessionId] ?? EMPTY_MESSAGES),
  )
  const taskRunsById = useTaskRunStore((state) => state.taskRunsById)
  const stepRunsById = useTaskRunStore((state) => state.stepRunsById)
  const approvalsById = useTaskRunStore((state) => state.approvalsById)
  const eventsByTaskRunId = useTaskRunStore((state) => state.eventsByTaskRunId)
  const replayNeededByTaskRunId = useTaskRunStore((state) => state.replayNeededByTaskRunId)
  const fetchSnapshot = useTaskRunStore((state) => state.fetchSnapshot)
  const replayEvents = useTaskRunStore((state) => state.replayEvents)

  const taskRunIds = useMemo(() => {
    const ids = new Set<string>()

    messages.forEach((message) => {
      if (message.taskRunId !== undefined) {
        ids.add(message.taskRunId)
      }
    })

    Object.values(taskRunsById).forEach((taskRun) => {
      if (taskRun.session_id === sessionId) {
        ids.add(taskRun.task_run_id)
      }
    })

    return [...ids]
  }, [messages, sessionId, taskRunsById])
  const taskRunSummaries = useMemo(
    () =>
      taskRunIds
        .map((taskRunId) =>
          toTaskRunSummaryView(taskRunsById[taskRunId], eventsByTaskRunId[taskRunId] ?? []),
        )
        .sort((first, second) => (second.lastSequence ?? 0) - (first.lastSequence ?? 0)),
    [eventsByTaskRunId, taskRunIds, taskRunsById],
  )
  const resolvedSelectedTaskRunId =
    selectedTaskRunId !== undefined && taskRunIds.includes(selectedTaskRunId)
      ? selectedTaskRunId
      : taskRunSummaries[0]?.id
  const selectedTaskRun =
    resolvedSelectedTaskRunId === undefined ? undefined : taskRunsById[resolvedSelectedTaskRunId]
  const selectedEvents = useMemo(
    () =>
      resolvedSelectedTaskRunId === undefined
        ? []
        : (eventsByTaskRunId[resolvedSelectedTaskRunId] ?? []),
    [eventsByTaskRunId, resolvedSelectedTaskRunId],
  )
  const selectedActivities = useMemo(() => selectedEvents.map(toActivityItemView), [selectedEvents])
  const selectedStepRuns = useMemo(
    () =>
      Object.values(stepRunsById)
        .filter((stepRun) => stepRun.task_run_id === resolvedSelectedTaskRunId)
        .sort((first, second) => (first.sequence ?? 0) - (second.sequence ?? 0)),
    [resolvedSelectedTaskRunId, stepRunsById],
  )
  const selectedApprovals = useMemo(
    () =>
      Object.values(approvalsById)
        .filter((approval) => approval.task_run_id === resolvedSelectedTaskRunId)
        .sort((first, second) => getTime(first.created_at) - getTime(second.created_at)),
    [approvalsById, resolvedSelectedTaskRunId],
  )
  const selectedPrompt = useMemo(
    () => findPromptForTaskRun(messages, resolvedSelectedTaskRunId),
    [messages, resolvedSelectedTaskRunId],
  )

  useEffect(() => {
    if (selectedTaskRunId === undefined && resolvedSelectedTaskRunId !== undefined) {
      onSelectTaskRun(resolvedSelectedTaskRunId)
    }
  }, [onSelectTaskRun, resolvedSelectedTaskRunId, selectedTaskRunId])

  useEffect(() => {
    if (resolvedSelectedTaskRunId === undefined) return

    void fetchSnapshot(resolvedSelectedTaskRunId).catch(() => undefined)
    void replayEvents(resolvedSelectedTaskRunId).catch(() => undefined)
  }, [fetchSnapshot, replayEvents, resolvedSelectedTaskRunId])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-border border-b p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-muted-foreground truncate text-xs">세션 {sessionId}</p>
            <h2 className="text-foreground mt-1 text-sm font-semibold">진행 상황</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="활동 패널 닫기"
            className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="border-border min-h-0 border-b p-3">
        {taskRunSummaries.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
            아직 표시할 진행 기록이 없습니다. 답변이 시작되면 여기에 상태가 표시됩니다.
          </div>
        ) : (
          <div className="space-y-2">
            {taskRunSummaries.map((summary) => (
              <button
                key={summary.id}
                type="button"
                onClick={() => onSelectTaskRun(summary.id)}
                aria-label={`답변 진행 상태 보기`}
                className={`border-border bg-card hover:bg-muted/60 flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                  resolvedSelectedTaskRunId === summary.id ? 'ring-ring ring-2' : ''
                }`}
              >
                <StatusIcon tone={summary.tone} />
                <span className="min-w-0 flex-1">
                  <span className="text-foreground block truncate text-sm font-medium">
                    {toUserFacingTaskTitle(summary.title)}
                  </span>
                  <span className="text-muted-foreground mt-1 block text-xs">
                    {summary.statusText}
                    {summary.lastSequence !== undefined ? ` · #${summary.lastSequence}` : ''}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {resolvedSelectedTaskRunId === undefined ? (
          <div className="text-muted-foreground text-sm">선택할 진행 기록이 없습니다.</div>
        ) : (
          <SelectedTaskRunView
            taskRunId={resolvedSelectedTaskRunId}
            taskRun={selectedTaskRun}
            prompt={selectedPrompt}
            steps={selectedStepRuns}
            approvals={selectedApprovals}
            activities={selectedActivities}
            replayNeeded={replayNeededByTaskRunId[resolvedSelectedTaskRunId] === true}
          />
        )}
      </div>
    </div>
  )
}

function SelectedTaskRunView({
  taskRunId,
  taskRun,
  prompt,
  steps,
  approvals,
  activities,
  replayNeeded,
}: {
  taskRunId: string
  taskRun?: RawTaskRun
  prompt?: string
  steps: RawStepRun[]
  approvals: RawApproval[]
  activities: ReturnType<typeof toActivityItemView>[]
  replayNeeded: boolean
}) {
  const status =
    taskRun?.status ?? activities.at(-1)?.raw.status ?? activities.at(-1)?.raw.event_type
  const recentActivities = activities.slice(-5).reverse()

  return (
    <div className="space-y-5">
      <section className="bg-card border-border rounded-lg border p-3">
        <div className="flex items-start gap-3">
          <StatusIcon tone={toTaskRunStatusTone(status)} />
          <div className="min-w-0 flex-1">
            <h3 className="text-foreground truncate text-sm font-semibold">
              {getAnswerProgressTitle(taskRun, prompt)}
            </h3>
            {prompt && <p className="text-muted-foreground mt-1 line-clamp-2 text-xs">{prompt}</p>}
            <p className="text-muted-foreground mt-2 text-sm">{toProgressSentence(status)}</p>
          </div>
        </div>
        {replayNeeded && (
          <div className="border-border bg-muted/40 text-muted-foreground mt-3 flex items-center gap-2 rounded-md border px-2.5 py-2 text-xs">
            <RotateCcw className="h-3.5 w-3.5" />
            이벤트 중간 구간 재조회가 필요합니다.
          </div>
        )}
      </section>

      {approvals.map((approval) => (
        <ApprovalCard key={approval.approval_id} approval={approval} taskRunId={taskRunId} />
      ))}

      <section>
        <h3 className="text-foreground mb-2 text-xs font-semibold">진행 단계</h3>
        {steps.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
            아직 세부 단계가 없습니다.
          </div>
        ) : (
          <ol className="space-y-2">
            {steps.map((step) => (
              <StepProgressItem
                key={step.step_run_id}
                step={step}
                activities={activities.filter(
                  (activity) => activity.stepRunId === step.step_run_id,
                )}
              />
            ))}
          </ol>
        )}
      </section>

      <section>
        <details className="group">
          <summary className="text-foreground hover:bg-muted flex cursor-pointer list-none items-center justify-between rounded-lg px-2 py-2 text-xs font-semibold transition-colors">
            <span>세부 기록</span>
            <span className="text-muted-foreground text-[11px]">{activities.length}개</span>
          </summary>
          {activities.length === 0 ? (
            <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
              아직 이벤트가 없습니다.
            </div>
          ) : (
            <ol className="mt-2 space-y-2">
              {recentActivities.map((activity) => (
                <ActivityEventItem key={activity.id} activity={activity} />
              ))}
            </ol>
          )}
        </details>
      </section>
    </div>
  )
}

function StepProgressItem({
  step,
  activities,
}: {
  step: RawStepRun
  activities: ReturnType<typeof toActivityItemView>[]
}) {
  return (
    <li className="bg-card border-border rounded-lg border">
      <details>
        <summary className="hover:bg-muted/60 flex cursor-pointer list-none items-start gap-3 rounded-lg p-3 transition-colors">
          <StatusIcon tone={toTaskRunStatusTone(step.status)} />
          <span className="min-w-0 flex-1">
            <span className="text-foreground block truncate text-sm font-medium">
              {toUserFacingTaskTitle(step.title ?? step.goal ?? '답변 준비')}
            </span>
            <span className="text-muted-foreground mt-1 block text-xs">
              {toProgressSentence(step.status)}
            </span>
          </span>
          <span className="text-muted-foreground text-[11px]">{activities.length}개</span>
        </summary>
        <div className="border-border border-t p-3">
          {activities.length === 0 ? (
            <p className="text-muted-foreground text-xs">아직 세부 기록이 없습니다.</p>
          ) : (
            <ol className="space-y-2">
              {activities.map((activity) => (
                <ActivityEventItem key={activity.id} activity={activity} />
              ))}
            </ol>
          )}
        </div>
      </details>
    </li>
  )
}

function ActivityEventItem({ activity }: { activity: ReturnType<typeof toActivityItemView> }) {
  return (
    <li className="bg-muted/30 border-border rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <StatusIcon tone={activity.tone} />
        <div className="min-w-0 flex-1">
          <p className="text-foreground text-sm font-medium">
            {toUserFacingTaskTitle(activity.title)}
          </p>
          <p className="text-muted-foreground mt-1 text-xs leading-5">
            {toProgressSentence(activity.raw.status ?? activity.raw.event_type)}
            {activity.sequence !== undefined ? ` · #${activity.sequence}` : ''}
          </p>
          {activity.occurredAt && (
            <p className="text-muted-foreground/80 mt-2 text-[11px]">{activity.occurredAt}</p>
          )}
        </div>
      </div>
    </li>
  )
}

function ApprovalCard({ approval, taskRunId }: { approval: RawApproval; taskRunId: string }) {
  const resumeTaskRun = useTaskRunStore((state) => state.resumeTaskRun)
  const cancelTaskRun = useTaskRunStore((state) => state.cancelTaskRun)
  const isApprovalSubmitting = useTaskRunStore((state) =>
    state.isApprovalSubmitting(approval.approval_id),
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const isActionable =
    approval.status === undefined || approval.status === null || approval.status === 'PENDING'
  const isButtonDisabled = isSubmitting || isApprovalSubmitting

  const handleResume = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await resumeTaskRun({
        taskRunId,
        approvalId: approval.approval_id,
        decision: 'APPROVED',
        response: { approved: true },
      })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '승인 응답 전송에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await resumeTaskRun({
        taskRunId,
        approvalId: approval.approval_id,
        decision: 'REJECTED',
        response: { approved: false },
      })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '거절 응답 전송에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await cancelTaskRun(taskRunId, 'approval cancelled from UI')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'TaskRun 취소에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="border-border bg-card rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
        <div className="min-w-0 flex-1">
          <h3 className="text-foreground text-sm font-semibold">
            {approval.title ?? '확인이 필요합니다'}
          </h3>
          {approval.description && (
            <p className="text-muted-foreground mt-1 text-xs leading-5">{approval.description}</p>
          )}
          <p className="text-muted-foreground mt-2 text-[11px]">
            approval {approval.approval_id} · {toApprovalStatusText(approval.status)}
          </p>
        </div>
      </div>
      {errorMessage && <p className="text-destructive mt-3 text-xs">{errorMessage}</p>}
      {isActionable && (
        <div className="mt-3 flex gap-2">
          <Button
            type="button"
            size="sm"
            onClick={handleResume}
            disabled={isButtonDisabled}
            aria-label={`Approval ${approval.approval_id} 승인 후 TaskRun 재개`}
          >
            {isButtonDisabled ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            승인
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleReject}
            disabled={isButtonDisabled}
            aria-label={`Approval ${approval.approval_id} 거절 후 TaskRun 재개`}
          >
            거절
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleCancel}
            disabled={isButtonDisabled}
            aria-label={`TaskRun ${taskRunId} 취소`}
          >
            작업 취소
          </Button>
        </div>
      )}
    </section>
  )
}

function StatusIcon({ tone }: { tone: TaskRunStatusTone }) {
  if (tone === 'completed')
    return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
  if (tone === 'failed') return <XCircle className="text-destructive mt-0.5 h-4 w-4 shrink-0" />
  if (tone === 'waiting') return <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
  if (tone === 'running') {
    return <Loader2 className="text-primary mt-0.5 h-4 w-4 shrink-0 animate-spin" />
  }
  return <FileText className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
}

function getTime(value?: string | null) {
  if (value === undefined || value === null) {
    return 0
  }
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}

function toApprovalStatusText(status?: string | null) {
  switch (status) {
    case 'APPROVED':
      return '승인됨'
    case 'REJECTED':
      return '거절됨'
    case 'CANCELLED':
      return '취소됨'
    case 'PENDING':
    case undefined:
    case null:
      return '대기 중'
    default:
      return status
  }
}

function useIsDesktopViewport() {
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window === 'undefined' ? true : window.matchMedia('(min-width: 1024px)').matches,
  )

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 1024px)')
    const handleChange = () => setIsDesktop(mediaQuery.matches)

    handleChange()
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return isDesktop
}

function findPromptForTaskRun(messages: ChatMessageView[], taskRunId?: string) {
  if (taskRunId === undefined) {
    return undefined
  }

  return messages.find((message) => message.role === 'user' && message.taskRunId === taskRunId)
    ?.content
}

function getAnswerProgressTitle(taskRun?: RawTaskRun, prompt?: string) {
  if (prompt !== undefined && prompt.trim() !== '') {
    return '질문에 대한 답변'
  }

  return toUserFacingTaskTitle(taskRun?.title ?? taskRun?.goal ?? '답변 준비')
}

function toUserFacingTaskTitle(value?: string | null) {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text) {
    return '답변 준비'
  }

  const normalized = text.toLowerCase()
  if (normalized.includes('agent.loop') || normalized.includes('agent loop')) {
    return '질문에 대한 답변'
  }
  if (normalized.includes('taskrun') || normalized.includes('steprun')) {
    return '답변 진행'
  }
  return text
}

function toProgressSentence(status?: string | null) {
  switch (status) {
    case 'PENDING':
    case 'accepted':
    case 'task.created':
      return '요청을 확인하고 있습니다.'
    case 'RUNNING':
    case 'step.started':
    case 'tool.started':
    case 'search.started':
    case 'session.message.delta':
      return '답변을 준비하는 중입니다.'
    case 'WAITING':
    case 'approval.required':
      return '추가 확인이 필요합니다.'
    case 'COMPLETED':
    case 'step.completed':
    case 'tool.completed':
    case 'search.completed':
    case 'session.message.completed':
      return '답변 준비가 완료되었습니다.'
    case 'FAILED':
      return '답변을 준비하는 중 문제가 발생했습니다.'
    case 'CANCELLED':
    case 'CANCELED':
      return '요청이 취소되었습니다.'
    default:
      return toTaskRunStatusText(status)
  }
}
