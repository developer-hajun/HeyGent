import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { TaskRunSummaryView } from '@/types/taskRuns'
import { toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusIcon } from './TaskRunStatusIcon'

export function TaskRunSummaryList({
  summaries,
  selectedTaskRunId,
  onSelectTaskRun,
  onFocusTaskRunMessage,
}: {
  summaries: TaskRunSummaryView[]
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string) => void
  onFocusTaskRunMessage?: (taskRunId: string) => void
}) {
  if (summaries.length === 0) {
    return (
      <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
        아직 표시할 진행 기록이 없습니다. 답변이 시작되면 여기에 상태가 표시됩니다.
      </div>
    )
  }

  const selectedIndex = Math.max(
    0,
    summaries.findIndex((summary) => summary.id === selectedTaskRunId),
  )
  const selectedSummary = summaries[selectedIndex] ?? summaries[0]
  const hasPrevious = selectedIndex > 0
  const hasNext = selectedIndex < summaries.length - 1

  const selectByIndex = (index: number) => {
    const nextSummary = summaries[index]
    if (nextSummary !== undefined) {
      onSelectTaskRun(nextSummary.id)
    }
  }

  return (
    <div className="grid grid-cols-[2rem_minmax(0,1fr)_2rem] items-center gap-2">
      {hasPrevious ? (
        <button
          type="button"
          onClick={() => selectByIndex(selectedIndex - 1)}
          aria-label="이전 답변 활동 보기"
          className="border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 items-center justify-center rounded-lg border transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      ) : (
        <div aria-hidden="true" />
      )}
      <button
        key={selectedSummary.id}
        type="button"
        onClick={() => onFocusTaskRunMessage?.(selectedSummary.id)}
        aria-label="해당 답변 위치로 이동"
        className="border-border bg-card hover:bg-muted/60 ring-ring flex h-20 min-w-0 items-center gap-3 rounded-lg border p-3 text-left ring-2 transition-colors"
      >
        <TaskRunStatusIcon tone={selectedSummary.tone} />
        <span className="flex min-w-0 flex-1 flex-col justify-center">
          <span className="text-foreground line-clamp-2 block text-sm leading-5 font-medium [overflow-wrap:anywhere] break-words">
            {toAlbumCardTitle(selectedSummary.title)}
          </span>
          <span className="text-muted-foreground mt-1 truncate text-xs">
            {selectedSummary.statusText}
          </span>
        </span>
      </button>
      {hasNext ? (
        <button
          type="button"
          onClick={() => selectByIndex(selectedIndex + 1)}
          aria-label="다음 답변 활동 보기"
          className="border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 items-center justify-center rounded-lg border transition-colors"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      ) : (
        <div aria-hidden="true" />
      )}
    </div>
  )
}

function toAlbumCardTitle(title: string) {
  const normalizedTitle = toUserFacingTaskTitle(title).replace(/\s+/g, ' ').trim()
  if (normalizedTitle.length <= 46) {
    return normalizedTitle
  }
  return `${normalizedTitle.slice(0, 46).trimEnd()}...`
}
