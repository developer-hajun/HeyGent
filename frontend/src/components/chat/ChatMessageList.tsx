import { ArrowDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ChatMessageItem } from './ChatMessageItem'
import type { ChatMessageView } from '@/types/aiChat'
import type { ActivityItemView, TaskRunSummaryView } from '@/types/taskRuns'

type ChatMessageListProps = {
  messages: ChatMessageView[]
  activitiesByTaskRunId: Record<string, ActivityItemView[]>
  taskRunSummariesById: Record<string, TaskRunSummaryView>
  onOpenTaskRun: (taskRunId: string) => void
}

export function ChatMessageList({
  messages,
  activitiesByTaskRunId,
  taskRunSummariesById,
  onOpenTaskRun,
}: ChatMessageListProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const [showJump, setShowJump] = useState(false)

  useEffect(() => {
    const element = scrollRef.current
    if (!element) return
    const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight
    if (distanceFromBottom < 140) {
      element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
      setShowJump(false)
    } else {
      setShowJump(true)
    }
  }, [messages])

  return (
    <div ref={scrollRef} className="relative min-h-0 flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {messages.map((message) => (
          <ChatMessageItem
            key={message.id}
            message={message}
            activities={
              message.taskRunId === undefined
                ? []
                : (activitiesByTaskRunId[message.taskRunId] ?? [])
            }
            taskRunSummary={
              message.taskRunId === undefined ? undefined : taskRunSummariesById[message.taskRunId]
            }
            onOpenTaskRun={onOpenTaskRun}
          />
        ))}
      </div>
      {showJump && (
        <button
          type="button"
          onClick={() =>
            scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
          }
          aria-label="새 메시지 위치로 이동"
          className="bg-popover text-foreground border-border absolute right-6 bottom-6 flex items-center gap-1.5 rounded-full border px-3 py-2 text-xs shadow-sm"
        >
          <ArrowDown className="h-3.5 w-3.5" />새 메시지
        </button>
      )}
    </div>
  )
}
