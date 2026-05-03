import { Bot, CheckCircle2, Clock3, Loader2, UserRound, XCircle } from 'lucide-react'
import type { ChatMessageView } from '@/types/aiChat'
import type { ActivityItemView, TaskRunSummaryView, TaskRunStatusTone } from '@/types/taskRuns'

type ChatMessageItemProps = {
  message: ChatMessageView
  activities?: ActivityItemView[]
  taskRunSummary?: TaskRunSummaryView
  onOpenTaskRun?: (taskRunId: string) => void
}

export function ChatMessageItem({
  message,
  activities = [],
  taskRunSummary,
  onOpenTaskRun,
}: ChatMessageItemProps) {
  const isUser = message.role === 'user'
  const taskRunChip = isUser ? undefined : getAssistantTaskRunChip(activities, taskRunSummary)

  return (
    <article className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="bg-primary/10 text-primary mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={`max-w-[78%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={
            isUser
              ? 'bg-primary text-primary-foreground rounded-2xl px-4 py-3 text-sm leading-6'
              : 'text-foreground rounded-2xl py-2 text-sm leading-7'
          }
        >
          {message.content ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>응답을 작성하는 중입니다.</span>
            </div>
          )}
        </div>
        {message.taskRunId && taskRunChip && (
          <button
            type="button"
            onClick={() => onOpenTaskRun?.(message.taskRunId as string)}
            aria-label="답변 진행 상황 열기"
            className="text-muted-foreground hover:text-foreground hover:bg-muted inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs transition-colors"
          >
            <TaskRunChipIcon tone={taskRunChip.tone} />
            <span>{taskRunChip.text}</span>
          </button>
        )}
      </div>
      {isUser && (
        <div className="bg-muted text-muted-foreground mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </article>
  )
}

function getAssistantTaskRunChip(
  activities: ActivityItemView[],
  taskRunSummary?: TaskRunSummaryView,
): { text: string; tone: TaskRunStatusTone } | undefined {
  const latestActivity = activities.at(-1)
  const taskStatus =
    typeof taskRunSummary?.raw?.status === 'string' ? taskRunSummary.raw.status : undefined
  const latestEventType = latestActivity?.raw.event_type

  if (taskStatus === 'COMPLETED' || isAnswerCompletionEvent(latestEventType)) {
    return { text: '답변 완료', tone: 'completed' }
  }

  if (
    latestActivity !== undefined &&
    latestActivity.tone === 'completed' &&
    !isAnswerCompletionEvent(latestEventType)
  ) {
    return { text: '답변 진행 중', tone: 'running' }
  }

  if (latestActivity !== undefined) {
    return { text: latestActivity.statusText, tone: latestActivity.tone }
  }

  if (taskRunSummary !== undefined) {
    return { text: taskRunSummary.statusText, tone: taskRunSummary.tone }
  }

  return undefined
}

function isAnswerCompletionEvent(eventType?: string) {
  return eventType === 'task.completed' || eventType === 'session.message.completed'
}

function TaskRunChipIcon({ tone }: { tone: TaskRunStatusTone }) {
  if (tone === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
  if (tone === 'failed') return <XCircle className="text-destructive h-3.5 w-3.5" />
  if (tone === 'waiting') return <Clock3 className="h-3.5 w-3.5 text-amber-500" />
  if (tone === 'running') return <Loader2 className="text-primary h-3.5 w-3.5 animate-spin" />
  return <Clock3 className="h-3.5 w-3.5" />
}
