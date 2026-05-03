import { Bot, CheckCircle2, Loader2, UserRound } from 'lucide-react'
import type { ActivityItemView, ChatMessageView } from './chatTypes'

type ChatMessageItemProps = {
  message: ChatMessageView
  activity?: ActivityItemView | null
  onOpenActivity?: () => void
}

export function ChatMessageItem({ message, activity, onOpenActivity }: ChatMessageItemProps) {
  const isUser = message.role === 'user'

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
        {message.role === 'assistant' && activity && (
          <button
            type="button"
            onClick={onOpenActivity}
            className="text-muted-foreground hover:text-foreground hover:bg-muted inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs transition-colors"
          >
            {activity.tone === 'completed' ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            )}
            <span>{activity.statusText}</span>
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
