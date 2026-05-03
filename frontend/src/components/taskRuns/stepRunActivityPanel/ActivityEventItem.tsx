import type { ActivityItemView } from '@/types/taskRuns'
import { toProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function ActivityEventItem({ activity }: { activity: ActivityItemView }) {
  return (
    <li className="bg-muted/30 border-border rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <TaskRunStatusIcon tone={activity.tone} />
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
