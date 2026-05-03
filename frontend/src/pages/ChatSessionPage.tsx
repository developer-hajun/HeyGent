import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { ChatEmptyState } from '@/components/chat/ChatEmptyState'
import { ChatMessageList } from '@/components/chat/ChatMessageList'
import { ChatSessionHeader } from '@/components/chat/ChatSessionHeader'
import { listSessionMessages, sendSessionMessageCreate } from '@/components/chat/aiChatCommands'
import type {
  ActivityItemView,
  ChatConnectionState,
  ChatMessageView,
} from '@/components/chat/chatTypes'
import { StepRunActivityPanel } from '@/components/taskRuns/StepRunActivityPanel'

type LoadState = 'loading' | 'ready' | 'error'

export function ChatSessionPage() {
  const { sessionId = '' } = useParams()
  const [messages, setMessages] = useState<ChatMessageView[]>([])
  const [activities, setActivities] = useState<ActivityItemView[]>([])
  const [activityOpen, setActivityOpen] = useState(false)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [connectionState, setConnectionState] = useState<ChatConnectionState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)

  const title = useMemo(() => `세션 ${sessionId}`, [sessionId])
  const latestActivity = activities[0] ?? null

  const loadMessages = useCallback(async () => {
    if (!sessionId) return
    setLoadState('loading')
    setConnectionState('connecting')
    setErrorMessage(null)
    setActivityOpen(false)

    try {
      const loaded = await listSessionMessages(sessionId)
      setMessages(loaded)
      setConnectionState('connected')
      setLoadState('ready')
    } catch (error) {
      setMessages([])
      setConnectionState('error')
      setLoadState('error')
      setErrorMessage(error instanceof Error ? error.message : '세션 메시지를 불러오지 못했습니다.')
    }
  }, [sessionId])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadMessages()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadMessages])

  const handleSend = async (content: string) => {
    if (!sessionId || isSending) return
    setIsSending(true)
    setConnectionState((state) => (state === 'error' ? 'reconnecting' : 'connected'))

    const clientMessageId = `pending_${Date.now()}`
    const assistantPlaceholderId = `assistant_${clientMessageId}`

    // optimistic 병합 지점: 서버 accepted가 오기 전에도 사용자 입력과 assistant placeholder를 먼저 그린다.
    setMessages((current) => [
      ...current,
      {
        id: clientMessageId,
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
        status: 'optimistic',
        clientMessageId,
      },
      {
        id: assistantPlaceholderId,
        role: 'assistant',
        content: '',
        createdAt: new Date().toISOString(),
        status: 'streaming',
      },
    ])
    setActivities((current) => [
      {
        id: `activity_${clientMessageId}`,
        title: '요청 접수 중',
        statusText: '서버 accepted 응답을 기다리는 중입니다.',
        tone: 'running',
        occurredAt: new Date().toLocaleTimeString('ko-KR'),
      },
      ...current,
    ])

    try {
      await sendSessionMessageCreate({
        sessionId,
        content,
        callbacks: {
          onAccepted: (accepted) => {
            // accepted 병합 지점: 이후 화면 key는 서버/DB ID를 우선 사용한다.
            setMessages((current) =>
              current.map((message) => {
                if (message.id === clientMessageId) {
                  return {
                    ...message,
                    id: accepted.userMessageId ?? message.id,
                    status: 'accepted',
                  }
                }
                if (message.id === assistantPlaceholderId) {
                  return {
                    ...message,
                    id: accepted.assistantMessageId ?? message.id,
                    taskRunId: accepted.taskRunId,
                    status: 'streaming',
                  }
                }
                return message
              }),
            )
            setActivities((current) => [
              {
                id: accepted.taskRunId ?? `accepted_${clientMessageId}`,
                title: '작업 시작',
                statusText: '요청이 접수되어 assistant가 응답을 준비하고 있습니다.',
                tone: 'running',
                occurredAt: new Date().toLocaleTimeString('ko-KR'),
              },
              ...current,
            ])
          },
          onDelta: (delta) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantPlaceholderId || message.status === 'streaming'
                  ? { ...message, content: `${message.content}${delta}`, status: 'streaming' }
                  : message,
              ),
            )
          },
          onCompleted: (finalContent) => {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantPlaceholderId || message.status === 'streaming'
                  ? {
                      ...message,
                      content: finalContent || message.content,
                      status: 'completed',
                    }
                  : message,
              ),
            )
            setActivities((current) => [
              {
                id: `completed_${clientMessageId}`,
                title: '응답 완료',
                statusText: 'assistant 응답이 완료되었습니다.',
                tone: 'completed',
                occurredAt: new Date().toLocaleTimeString('ko-KR'),
              },
              ...current,
            ])
          },
          onTaskEvent: (event) => {
            // 활동 패널은 raw event 이름을 그대로 노출하지 않고 사용자가 이해하는 상태 문구로 축약한다.
            setActivities((current) => [
              {
                id: event.event_id,
                title: event.summary_message ?? '작업 진행',
                statusText: event.status ?? event.event_type,
                tone:
                  event.status === 'FAILED'
                    ? 'failed'
                    : event.status === 'COMPLETED'
                      ? 'completed'
                      : 'running',
                occurredAt: event.occurred_at ?? undefined,
              },
              ...current,
            ])
          },
        },
      })
      setConnectionState('connected')
    } catch (error) {
      setConnectionState('error')
      setErrorMessage(error instanceof Error ? error.message : '메시지 전송에 실패했습니다.')
      setMessages((current) =>
        current.map((message) =>
          message.id === clientMessageId || message.id === assistantPlaceholderId
            ? {
                ...message,
                status: 'failed',
                content:
                  message.role === 'assistant' ? '응답을 시작하지 못했습니다.' : message.content,
              }
            : message,
        ),
      )
      setActivities((current) => [
        {
          id: `failed_${clientMessageId}`,
          title: '전송 실패',
          statusText: '연결 상태를 확인한 뒤 다시 시도해 주세요.',
          tone: 'failed',
          occurredAt: new Date().toLocaleTimeString('ko-KR'),
        },
        ...current,
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <main className="bg-background flex min-w-0 flex-1 overflow-hidden">
      <section className="flex min-w-0 flex-1 flex-col">
        <ChatSessionHeader
          title={title}
          connectionState={connectionState}
          onOpenActivity={() => setActivityOpen(true)}
        />
        {errorMessage && loadState !== 'error' && (
          <button
            type="button"
            onClick={() => setActivityOpen(true)}
            className="border-border bg-muted/40 text-muted-foreground hover:text-foreground flex items-center justify-center gap-2 border-b px-4 py-2 text-xs transition-colors"
          >
            <AlertCircle className="h-3.5 w-3.5" />
            <span>{errorMessage}</span>
          </button>
        )}
        {loadState === 'loading' ? (
          <div className="text-muted-foreground flex min-h-0 flex-1 items-center justify-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            메시지를 불러오는 중입니다.
          </div>
        ) : loadState === 'error' ? (
          <div className="flex min-h-0 flex-1 items-center justify-center px-6">
            <div className="border-border bg-card max-w-md rounded-lg border p-5 text-center shadow-sm">
              <AlertCircle className="text-destructive mx-auto h-6 w-6" />
              <h2 className="text-foreground mt-3 text-sm font-semibold">
                세션을 불러오지 못했습니다
              </h2>
              <p className="text-muted-foreground mt-2 text-sm leading-6">{errorMessage}</p>
              <button
                type="button"
                onClick={() => void loadMessages()}
                className="bg-primary text-primary-foreground hover:bg-primary/90 mt-4 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
              >
                <RefreshCw className="h-4 w-4" />
                다시 시도
              </button>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <ChatEmptyState sessionId={sessionId} />
        ) : (
          <ChatMessageList
            messages={messages}
            latestActivity={latestActivity}
            onOpenActivity={() => setActivityOpen(true)}
          />
        )}
        <ChatComposer
          disabled={connectionState === 'auth-expired'}
          isSending={isSending}
          onSend={handleSend}
        />
      </section>
      <StepRunActivityPanel
        open={activityOpen}
        onOpenChange={setActivityOpen}
        sessionId={sessionId}
        items={activities}
      />
    </main>
  )
}
