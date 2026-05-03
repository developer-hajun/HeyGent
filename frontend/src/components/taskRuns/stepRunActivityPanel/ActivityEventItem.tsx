import { ChevronDown } from 'lucide-react'
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
    <li className="bg-muted/30 border-border rounded-lg border">
      <details className="group">
        <summary className="hover:bg-muted/50 flex min-h-20 cursor-pointer list-none items-center gap-3 rounded-lg p-3 transition-colors">
          <TaskRunStatusIcon tone={tone} />
          <span className="min-w-0 flex-1">
            <span className="text-foreground line-clamp-2 block text-sm font-medium [overflow-wrap:anywhere] break-words">
              {toUserFacingTaskTitle(activity.title)}
            </span>
            <span className="text-muted-foreground mt-1 line-clamp-1 block text-xs leading-5 [overflow-wrap:anywhere] break-words">
              {toProgressSentence(activity.raw.status ?? activity.raw.event_type)}
            </span>
          </span>
          <ChevronDown className="text-muted-foreground h-4 w-4 shrink-0 transition-transform group-open:rotate-180" />
        </summary>
        {activity.occurredAt && (
          <div className="border-border text-muted-foreground/80 border-t px-3 py-2 pl-12 text-[11px]">
            {activity.occurredAt}
          </div>
        )}
      </details>
    </li>
  )
}
