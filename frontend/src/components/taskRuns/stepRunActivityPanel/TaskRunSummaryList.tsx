import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef } from 'react'
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
  const scrollRef = useRef<HTMLDivElement | null>(null)

  if (summaries.length === 0) {
    return (
      <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
        아직 표시할 진행 기록이 없습니다. 답변이 시작되면 여기에 상태가 표시됩니다.
      </div>
    )
  }

  const scrollByCard = (direction: 'left' | 'right') => {
    scrollRef.current?.scrollBy({
      left: direction === 'left' ? -280 : 280,
      behavior: 'smooth',
    })
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => scrollByCard('left')}
        aria-label="이전 답변 활동 보기"
        className="border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:opacity-40"
        disabled={summaries.length <= 1}
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <div
        ref={scrollRef}
        className="scrollbar-thin flex min-w-0 flex-1 snap-x gap-2 overflow-x-auto py-1"
      >
        {summaries.map((summary) => (
          <button
            key={summary.id}
            type="button"
            onClick={() => onSelectTaskRun(summary.id)}
            aria-label="답변 진행 상태 보기"
            className={`border-border bg-card hover:bg-muted/60 flex min-h-20 w-64 shrink-0 snap-start items-center gap-3 rounded-lg border p-3 text-left transition-colors ${
              selectedTaskRunId === summary.id ? 'ring-ring ring-2' : ''
            }`}
          >
            <TaskRunStatusIcon tone={summary.tone} />
            <span className="min-w-0 flex-1">
              <span className="text-foreground line-clamp-2 block text-sm font-medium [overflow-wrap:anywhere] break-words">
                {toUserFacingTaskTitle(summary.title)}
              </span>
              <span className="text-muted-foreground mt-1 line-clamp-1 block text-xs">
                {summary.statusText}
              </span>
            </span>
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => scrollByCard('right')}
        aria-label="다음 답변 활동 보기"
        className="border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:opacity-40"
        disabled={summaries.length <= 1}
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}
