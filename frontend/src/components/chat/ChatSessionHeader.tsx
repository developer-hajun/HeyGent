import { AlertCircle, Loader2, MessageCircle, PanelRightOpen, Settings, Wifi } from 'lucide-react'
import type { ChatConnectionState } from './chatTypes'

type ChatSessionHeaderProps = {
  title: string
  connectionState: ChatConnectionState
  onOpenActivity: () => void
  onOpenSettings: () => void
}

const connectionText: Record<ChatConnectionState, string> = {
  idle: '대기 중',
  connecting: '연결 중',
  connected: '연결됨',
  reconnecting: '연결 복구 중',
  error: '연결 오류',
  'auth-expired': '인증 필요',
}

export function ChatSessionHeader({
  title,
  connectionState,
  onOpenActivity,
  onOpenSettings,
}: ChatSessionHeaderProps) {
  const isBusy = connectionState === 'connecting' || connectionState === 'reconnecting'
  const isError = connectionState === 'error' || connectionState === 'auth-expired'

  return (
    <header className="bg-background/95 supports-backdrop-filter:bg-background/80 relative flex h-12 shrink-0 flex-col justify-center backdrop-blur">
      <div className="flex items-center justify-between px-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="bg-muted text-muted-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
            <MessageCircle className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h1 className="text-foreground truncate text-sm font-semibold">{title}</h1>
            <div
              className={`flex items-center gap-1.5 text-xs ${
                isError ? 'text-destructive' : 'text-muted-foreground'
              }`}
            >
              {isBusy ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : isError ? (
                <AlertCircle className="h-3 w-3" />
              ) : (
                <Wifi className="h-3 w-3" />
              )}
              <span>{connectionText[connectionState]}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onOpenSettings}
            className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            aria-label="세션 설정 열기"
          >
            <Settings className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onOpenActivity}
            className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            aria-label="활동 패널 열기"
          >
            <PanelRightOpen className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="border-border/60 absolute right-4 bottom-0 left-4 border-b" />
    </header>
  )
}
