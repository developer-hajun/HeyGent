import {
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  RotateCcw,
  ShieldCheck,
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
  return (
    <>
      {open && (
        <aside className="border-border bg-popover hidden w-96 shrink-0 flex-col border-l lg:flex">
          <PanelBody
            sessionId={sessionId}
            selectedTaskRunId={selectedTaskRunId}
            onSelectTaskRun={onSelectTaskRun}
          />
        </aside>
      )}
      <div className="lg:hidden">
        <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
          <DrawerContent className="bg-popover max-h-[86vh] p-0">
            <DrawerHeader className="sr-only">
              <DrawerTitle>TaskRun 활동</DrawerTitle>
              <DrawerDescription>
                현재 세션의 TaskRun, StepRun, 이벤트 상태입니다.
              </DrawerDescription>
            </DrawerHeader>
            <PanelBody
              sessionId={sessionId}
              selectedTaskRunId={selectedTaskRunId}
              onSelectTaskRun={onSelectTaskRun}
            />
          </DrawerContent>
        </Drawer>
      </div>
    </>
  )
}

function PanelBody({
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
}: {
  sessionId: string
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string | undefined) => void
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
        <p className="text-muted-foreground text-xs">세션 {sessionId}</p>
        <h2 className="text-foreground mt-1 text-sm font-semibold">TaskRun 추적</h2>
      </div>
      <div className="border-border min-h-0 border-b p-3">
        {taskRunSummaries.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
            아직 연결된 TaskRun이 없습니다. assistant 응답이 시작되면 작업 카드가 표시됩니다.
          </div>
        ) : (
          <div className="space-y-2">
            {taskRunSummaries.map((summary) => (
              <button
                key={summary.id}
                type="button"
                onClick={() => onSelectTaskRun(summary.id)}
                aria-label={`TaskRun ${summary.id} 상태 보기`}
                className={`border-border bg-card hover:bg-muted/60 flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                  resolvedSelectedTaskRunId === summary.id ? 'ring-ring ring-2' : ''
                }`}
              >
                <StatusIcon tone={summary.tone} />
                <span className="min-w-0 flex-1">
                  <span className="text-foreground block truncate text-sm font-medium">
                    {summary.title}
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
          <div className="text-muted-foreground text-sm">선택할 TaskRun이 없습니다.</div>
        ) : (
          <SelectedTaskRunView
            taskRunId={resolvedSelectedTaskRunId}
            taskRun={selectedTaskRun}
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
  steps,
  approvals,
  activities,
  replayNeeded,
}: {
  taskRunId: string
  taskRun?: RawTaskRun
  steps: RawStepRun[]
  approvals: RawApproval[]
  activities: ReturnType<typeof toActivityItemView>[]
  replayNeeded: boolean
}) {
  const status =
    taskRun?.status ?? activities.at(-1)?.raw.status ?? activities.at(-1)?.raw.event_type

  return (
    <div className="space-y-5">
      <section className="bg-card border-border rounded-lg border p-3">
        <div className="flex items-start gap-3">
          <StatusIcon tone={toTaskRunStatusTone(status)} />
          <div className="min-w-0 flex-1">
            <h3 className="text-foreground truncate text-sm font-semibold">
              {taskRun?.title ?? taskRun?.goal ?? 'TaskRun'}
            </h3>
            <p className="text-muted-foreground mt-1 text-xs">{taskRunId}</p>
            <p className="text-muted-foreground mt-2 text-sm">{toTaskRunStatusText(status)}</p>
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
        <h3 className="text-foreground mb-2 text-xs font-semibold">StepRun</h3>
        {steps.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
            아직 StepRun 스냅샷이 없습니다.
          </div>
        ) : (
          <ol className="space-y-2">
            {steps.map((step) => (
              <li key={step.step_run_id} className="bg-card border-border rounded-lg border p-3">
                <div className="flex items-start gap-3">
                  <StatusIcon tone={toTaskRunStatusTone(step.status)} />
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground truncate text-sm font-medium">
                      {step.title ?? step.goal ?? 'StepRun'}
                    </p>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {toTaskRunStatusText(step.status)}
                      {step.sequence !== undefined && step.sequence !== null
                        ? ` · ${step.sequence}`
                        : ''}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section>
        <h3 className="text-foreground mb-2 text-xs font-semibold">Event timeline</h3>
        {activities.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
            아직 이벤트가 없습니다.
          </div>
        ) : (
          <ol className="space-y-2">
            {activities.map((activity) => (
              <li key={activity.id} className="bg-card border-border rounded-lg border p-3">
                <div className="flex items-start gap-3">
                  <StatusIcon tone={activity.tone} />
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground text-sm font-medium">{activity.title}</p>
                    <p className="text-muted-foreground mt-1 text-xs leading-5">
                      {activity.statusText}
                      {activity.sequence !== undefined ? ` · #${activity.sequence}` : ''}
                    </p>
                    {activity.occurredAt && (
                      <p className="text-muted-foreground/80 mt-2 text-[11px]">
                        {activity.occurredAt}
                      </p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}

function ApprovalCard({ approval, taskRunId }: { approval: RawApproval; taskRunId: string }) {
  const resumeTaskRun = useTaskRunStore((state) => state.resumeTaskRun)
  const cancelTaskRun = useTaskRunStore((state) => state.cancelTaskRun)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const isActionable =
    approval.status === undefined || approval.status === null || approval.status === 'PENDING'

  const handleResume = async () => {
    if (!isActionable) return
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

  const handleCancel = async () => {
    if (!isActionable) return
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
            disabled={isSubmitting}
            aria-label={`Approval ${approval.approval_id} 승인 후 TaskRun 재개`}
          >
            {isSubmitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            승인
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleCancel}
            disabled={isSubmitting}
            aria-label={`TaskRun ${taskRunId} 취소`}
          >
            취소
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
