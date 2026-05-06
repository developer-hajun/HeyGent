import { Bot, CheckCircle2, Clock3, Loader2, UserRound, XCircle } from 'lucide-react'
import type { ChatMessageView } from '@/types/aiChat'
import type {
  ActivityItemView,
  RawStepRun,
  TaskRunSummaryView,
  TaskRunStatusTone,
} from '@/types/taskRuns'
import { toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import {
  toStepProgressSentence,
  toUserFacingTaskTitle,
} from '@/components/taskRuns/stepRunActivityPanel/activityPanelText'
import { TaskRunStatusIcon } from '@/components/taskRuns/stepRunActivityPanel/TaskRunStatusIcon'

type ChatMessageItemProps = {
  message: ChatMessageView
  activities?: ActivityItemView[]
  stepRuns?: RawStepRun[]
  taskRunSummary?: TaskRunSummaryView
  onOpenTaskRun?: (taskRunId: string) => void
}

export function ChatMessageItem({
  message,
  activities = [],
  stepRuns = [],
  taskRunSummary,
  onOpenTaskRun,
}: ChatMessageItemProps) {
  const isUser = message.role === 'user'
  const taskRunChip = isUser ? undefined : getAssistantTaskRunChip(activities, taskRunSummary)
  const taskRunProgress = isUser ? undefined : getAssistantTaskRunProgress(stepRuns, taskRunSummary)
  const taskStatus =
    typeof taskRunSummary?.raw?.status === 'string' ? taskRunSummary.raw.status : undefined
  const shouldShowMessageBody =
    message.content.trim() !== '' ||
    isUser ||
    (!isTerminalTaskStatus(taskStatus) && !taskRunProgress)

  return (
    <article className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="bg-primary/10 text-primary mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={`max-w-[78%] space-y-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {shouldShowMessageBody && (
          <div
            className={
              isUser
                ? 'bg-primary text-primary-foreground rounded-2xl px-4 py-3 text-sm leading-6 [overflow-wrap:anywhere] break-words'
                : 'text-foreground rounded-2xl py-2 text-sm leading-7 [overflow-wrap:anywhere] break-words'
            }
          >
            {message.content.trim() !== '' ? (
              <p className="[overflow-wrap:anywhere] break-words whitespace-pre-wrap">
                {message.content}
              </p>
            ) : (
              <div className="text-muted-foreground flex items-center gap-2">
                {message.status === 'waiting' ? (
                  <>
                    <Clock3 className="h-4 w-4 text-amber-500" />
                    <span>사용자 확인을 기다리는 중입니다.</span>
                  </>
                ) : (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
              </div>
            )}
          </div>
        )}
        {message.taskRunId && taskRunProgress && (
          <button
            type="button"
            onClick={() => onOpenTaskRun?.(message.taskRunId as string)}
            aria-label="답변 진행 단계 열기"
            className="border-border bg-card hover:bg-muted/40 w-full max-w-xl rounded-lg border px-3 py-2 text-left shadow-sm transition-colors"
          >
            <ol className="space-y-1.5">
              {taskRunProgress.items.map((item) => (
                <li key={item.id} className="flex items-start gap-2">
                  <TaskRunStatusIcon tone={item.tone} />
                  <span className="min-w-0 flex-1">
                    <span className="text-foreground line-clamp-1 block text-xs font-medium [overflow-wrap:anywhere] break-words">
                      {item.text}
                    </span>
                    <span className="text-muted-foreground line-clamp-1 block text-[11px]">
                      {item.detail}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </button>
        )}
        {message.taskRunId && taskRunChip && taskRunProgress === undefined && (
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

type AssistantTaskRunProgress = {
  items: {
    id: string
    text: string
    detail: string
    tone: TaskRunStatusTone
  }[]
}

function getAssistantTaskRunProgress(
  stepRuns: RawStepRun[],
  taskRunSummary?: TaskRunSummaryView,
): AssistantTaskRunProgress | undefined {
  const taskStatus =
    typeof taskRunSummary?.raw?.status === 'string' ? taskRunSummary.raw.status : undefined
  if (isTerminalTaskStatus(taskStatus) || stepRuns.length === 0) {
    return undefined
  }

  const visibleSteps = stepRuns
    .filter((stepRun) => !isTerminalTaskStatus(stepRun.status) || stepRun.status === 'COMPLETED')
    .slice(-3)

  if (visibleSteps.length === 0) {
    return undefined
  }

  return {
    items: visibleSteps.map((stepRun) => {
      const title = toUserFacingTaskTitle(stepRun.title ?? stepRun.goal ?? '답변 진행')
      const status = stepRun.status
      return {
        id: stepRun.step_run_id,
        text: `${title}${toCompactStepSuffix(status)}`,
        detail: toStepProgressSentence(status),
        tone: toTaskRunStatusTone(status),
      }
    }),
  }
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

function isTerminalTaskStatus(status?: string | null) {
  return (
    status === 'COMPLETED' ||
    status === 'FAILED' ||
    status === 'CANCELLED' ||
    status === 'CANCELED' ||
    status === 'task.completed' ||
    status === 'task.failed' ||
    status === 'task.canceled'
  )
}

function toCompactStepSuffix(status?: string | null) {
  switch (status) {
    case 'COMPLETED':
    case 'step.completed':
      return ' 완료'
    case 'RUNNING':
    case 'step.started':
      return ' 중'
    case 'WAITING':
    case 'step.waiting':
      return ' 대기 중'
    case 'FAILED':
    case 'step.failed':
      return ' 실패'
    default:
      return ''
  }
}

function TaskRunChipIcon({ tone }: { tone: TaskRunStatusTone }) {
  if (tone === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
  if (tone === 'failed') return <XCircle className="text-destructive h-3.5 w-3.5" />
  if (tone === 'waiting') return <Clock3 className="h-3.5 w-3.5 text-amber-500" />
  if (tone === 'running') return <Loader2 className="text-primary h-3.5 w-3.5 animate-spin" />
  return <Clock3 className="h-3.5 w-3.5" />
}
