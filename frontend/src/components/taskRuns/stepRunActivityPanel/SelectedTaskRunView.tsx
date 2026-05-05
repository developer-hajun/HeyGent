import { RotateCcw } from 'lucide-react'
import type { ActivityItemView, RawApproval, RawStepRun, RawTaskRun } from '@/types/taskRuns'
import { toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import { ActivityEventItem } from './ActivityEventItem'
import { ApprovalCard } from './ApprovalCard'
import { StepProgressItem } from './StepProgressItem'
import { toStepProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function SelectedTaskRunView({
  taskRunId,
  taskRun,
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
  activities: ActivityItemView[]
  replayNeeded: boolean
}) {
  // snapshot이 아직 도착하지 않은 순간에는 raw event의 마지막 상태를 대표 상태로 쓴다.
  const status =
    activities.at(-1)?.raw.status ?? activities.at(-1)?.raw.event_type ?? taskRun?.status
  const taskRunFinished = status === 'COMPLETED' || status === 'task.completed'
  // 패널이 길어지지 않도록 세부 기록 본문에는 최신 raw event 5개만 펼쳐 보여준다.
  const recentActivities = activities.slice(-5).reverse()
  const currentStep = selectCurrentVisibleStep(taskRun, steps)
  const currentStepActivities =
    currentStep === undefined
      ? []
      : activities.filter((activity) => activity.stepRunId === currentStep.step_run_id)
  const latestCurrentActivity = currentStepActivities.at(-1) ?? activities.at(-1)

  return (
    <div className="space-y-5">
      {!taskRunFinished && (currentStep !== undefined || latestCurrentActivity !== undefined) && (
        <section className="border-border bg-muted/30 rounded-lg border px-3 py-2">
          <div className="flex items-start gap-2">
            <TaskRunStatusIcon tone={toTaskRunStatusTone(currentStep?.status ?? status)} />
            <div className="min-w-0">
              <div className="text-foreground line-clamp-1 text-xs font-semibold [overflow-wrap:anywhere] break-words">
                {toUserFacingTaskTitle(
                  currentStep?.title ?? currentStep?.goal ?? latestCurrentActivity?.title,
                )}
              </div>
              <div className="text-muted-foreground mt-0.5 line-clamp-1 text-[11px] [overflow-wrap:anywhere] break-words">
                {latestCurrentActivity?.title ??
                  toStepProgressSentence(currentStep?.status ?? status)}
              </div>
            </div>
          </div>
        </section>
      )}

      {replayNeeded && (
        <section className="border-border bg-muted/40 text-muted-foreground flex items-center gap-2 rounded-lg border px-3 py-2 text-xs">
          <RotateCcw className="h-3.5 w-3.5" />
          진행 기록 일부를 다시 불러와야 합니다.
        </section>
      )}

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
                // step_run_id가 있는 event만 해당 단계 아래에 묶고, 전체 진행 event는 아래 세부 기록에서 본다.
                activities={activities.filter(
                  (activity) => activity.stepRunId === step.step_run_id,
                )}
                taskRunFinished={taskRunFinished}
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
              아직 세부 기록이 없습니다.
            </div>
          ) : (
            <ol className="mt-2 space-y-2">
              {recentActivities.map((activity) => (
                <ActivityEventItem
                  key={activity.id}
                  activity={activity}
                  taskRunFinished={taskRunFinished}
                />
              ))}
            </ol>
          )}
        </details>
      </section>
    </div>
  )
}

function selectCurrentVisibleStep(taskRun: RawTaskRun | undefined, steps: RawStepRun[]) {
  const currentStepRunId =
    typeof taskRun?.current_step_run_id === 'string'
      ? taskRun.current_step_run_id
      : typeof taskRun?.currentStepRunId === 'string'
        ? taskRun.currentStepRunId
        : undefined

  if (currentStepRunId !== undefined) {
    const currentStep = steps.find((step) => step.step_run_id === currentStepRunId)
    if (currentStep !== undefined) {
      return currentStep
    }
  }

  return (
    steps.find((step) => step.status === 'RUNNING' || step.status === 'WAITING') ?? steps.at(-1)
  )
}
