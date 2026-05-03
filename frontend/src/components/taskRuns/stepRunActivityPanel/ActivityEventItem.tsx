import type { ActivityItemView } from '@/types/taskRuns'
import { toProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function ActivityEventItem({
  activity,
  taskRunFinished = false,
}: {
  activity: ActivityItemView
  taskRunFinished?: boolean
}) {
  // 세부 기록은 과거 이벤트의 상태를 보여준다. 다만 TaskRun이 이미 끝난 뒤에는
  // 과거 started/running 이벤트 아이콘이 계속 도는 것처럼 보이지 않게 고정 아이콘으로 바꾼다.
  const tone = taskRunFinished && activity.tone === 'running' ? 'completed' : activity.tone

  return (
    <li className="bg-muted/30 border-border rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <TaskRunStatusIcon tone={tone} />
        <div className="min-w-0 flex-1">
          <p className="text-foreground text-sm font-medium [overflow-wrap:anywhere] break-words">
            {toUserFacingTaskTitle(activity.title)}
          </p>
          <p className="text-muted-foreground mt-1 text-xs leading-5 [overflow-wrap:anywhere] break-words">
            {toProgressSentence(activity.raw.status ?? activity.raw.event_type)}
          </p>
          {activity.occurredAt && (
            <p className="text-muted-foreground/80 mt-2 text-[11px]">{activity.occurredAt}</p>
          )}
        </div>
      </div>
    </li>
  )
}
