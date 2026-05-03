import type { TaskRunSummaryView } from '@/types/taskRuns'
import { toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function TaskRunSummaryList({
  summaries,
  selectedTaskRunId,
  onSelectTaskRun,
}: {
  summaries: TaskRunSummaryView[]
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string) => void
}) {
  if (summaries.length === 0) {
    return (
      <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
        아직 표시할 진행 기록이 없습니다. 답변이 시작되면 여기에 상태가 표시됩니다.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {summaries.map((summary) => (
        <button
          key={summary.id}
          type="button"
          onClick={() => onSelectTaskRun(summary.id)}
          aria-label="답변 진행 상태 보기"
          className={`border-border bg-card hover:bg-muted/60 flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
            selectedTaskRunId === summary.id ? 'ring-ring ring-2' : ''
          }`}
        >
          <TaskRunStatusIcon tone={summary.tone} />
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
  )
}
