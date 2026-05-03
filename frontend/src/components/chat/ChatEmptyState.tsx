import { Bot, MessageCircle } from 'lucide-react'

type ChatEmptyStateProps = {
  sessionId: string
}

export function ChatEmptyState({ sessionId }: ChatEmptyStateProps) {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center px-6">
      <div className="max-w-md space-y-4 text-center">
        <div className="bg-primary/10 text-primary mx-auto flex h-14 w-14 items-center justify-center rounded-2xl">
          <Bot className="h-7 w-7" />
        </div>
        <div className="space-y-2">
          <h2 className="text-foreground text-lg font-semibold">대화를 이어갈 수 있습니다</h2>
          <p className="text-muted-foreground text-sm leading-6">
            세션 {sessionId}의 기존 메시지가 아직 없거나 조회되지 않았습니다. 아래 입력창에서 새
            메시지를 보내면 같은 세션으로 이어집니다.
          </p>
        </div>
        <div className="text-muted-foreground inline-flex items-center gap-1.5 text-xs">
          <MessageCircle className="h-3.5 w-3.5" />
          <span>활동 패널은 응답이 시작되면 열 수 있습니다.</span>
        </div>
      </div>
    </div>
  )
}
