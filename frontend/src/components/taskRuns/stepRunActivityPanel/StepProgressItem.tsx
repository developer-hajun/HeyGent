import type { ActivityItemView, RawStepRun } from '@/types/taskRuns'
import { toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import { ActivityEventItem } from './ActivityEventItem'
import { toProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function StepProgressItem({
  step,
  activities,
  taskRunFinished = false,
}: {
  step: RawStepRun
  activities: ActivityItemView[]
  taskRunFinished?: boolean
}) {
  return (
    <li className="bg-card border-border rounded-lg border">
      <details>
        <summary className="hover:bg-muted/60 flex cursor-pointer list-none items-start gap-3 rounded-lg p-3 transition-colors">
          <TaskRunStatusIcon tone={toTaskRunStatusTone(step.status)} />
          <span className="min-w-0 flex-1">
            <span className="text-foreground block text-sm font-medium [overflow-wrap:anywhere] break-words">
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
                <ActivityEventItem
                  key={activity.id}
                  activity={activity}
                  taskRunFinished={taskRunFinished || step.status === 'COMPLETED'}
                />
              ))}
            </ol>
          )}
        </div>
      </details>
    </li>
  )
}
