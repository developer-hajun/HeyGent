import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { ChatEmptyState } from '@/components/chat/ChatEmptyState'
import { ChatMessageList } from '@/components/chat/ChatMessageList'
import { ChatSessionHeader } from '@/components/chat/ChatSessionHeader'
import type { ChatConnectionState } from '@/components/chat/chatTypes'
import { StepRunActivityPanel } from '@/components/taskRuns/StepRunActivityPanel'
import type { AiRealtimeAuthStatus, AiRealtimeConnectionStatus } from '@/realtime/aiRealtimeTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import { toActivityItemView, toTaskRunSummaryView } from '@/utils/taskRunStatusView'

type LoadState = 'loading' | 'ready' | 'error'

const EMPTY_MESSAGES: never[] = []

export function ChatSessionPage() {
  const { sessionId = '' } = useParams()
  const [activityOpen, setActivityOpen] = useState(false)
  const [selectedTaskRunId, setSelectedTaskRunId] = useState<string | undefined>()
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const hydratedTaskRunIdsRef = useRef<Set<string>>(new Set())

  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const socketClient = useAiRealtimeStore((state) => state.socketClient)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const subscribeTask = useAiRealtimeStore((state) => state.subscribeTask)
  const accessToken = useAuthStore((state) => state.accessToken)

  const storeMessages = useChatStore((state) =>
    sessionId === '' ? EMPTY_MESSAGES : (state.messagesBySessionId[sessionId] ?? EMPTY_MESSAGES),
  )
  const isLoadingMessages = useChatStore((state) =>
    sessionId === '' ? false : state.loadingSessionIds[sessionId] === true,
  )
  const chatError = useChatStore((state) => state.lastError)
  const fetchMessages = useChatStore((state) => state.fetchMessages)
  const sendMessage = useChatStore((state) => state.sendMessage)

  const taskRunsById = useTaskRunStore((state) => state.taskRunsById)
  const eventsByTaskRunId = useTaskRunStore((state) => state.eventsByTaskRunId)
  const lastSequenceByTaskRunId = useTaskRunStore((state) => state.lastSequenceByTaskRunId)
  const taskRunError = useTaskRunStore((state) => state.lastError)
  const fetchActiveTaskRuns = useTaskRunStore((state) => state.fetchActiveTaskRuns)
  const fetchSnapshot = useTaskRunStore((state) => state.fetchSnapshot)
  const replayEvents = useTaskRunStore((state) => state.replayEvents)

  const title = useMemo(() => `세션 ${sessionId}`, [sessionId])
  const connectionState = useMemo(
    () => toChatConnectionState(connectionStatus, authStatus),
    [authStatus, connectionStatus],
  )
  const messages = useMemo(
    () =>
      storeMessages.filter((message) => message.role === 'user' || message.role === 'assistant'),
    [storeMessages],
  )
  const taskRunIds = useMemo(() => {
    const ids = new Set<string>()

    messages.forEach((message) => {
      if (message.taskRunId !== undefined) {
        ids.add(message.taskRunId)
      }
    })

    Object.values(taskRunsById).forEach((taskRun) => {
      if (taskRun.session_id === sessionId) {
        ids.add(taskRun.task_run_id)
      }
    })

    return [...ids]
  }, [messages, sessionId, taskRunsById])
  const taskRunIdKey = taskRunIds.join('|')
  const activitiesByTaskRunId = useMemo(
    () =>
      Object.fromEntries(
        taskRunIds.map((taskRunId) => [
          taskRunId,
          (eventsByTaskRunId[taskRunId] ?? []).map(toActivityItemView),
        ]),
      ),
    [eventsByTaskRunId, taskRunIds],
  )
  const taskRunSummariesById = useMemo(
    () =>
      Object.fromEntries(
        taskRunIds.map((taskRunId) => [
          taskRunId,
          toTaskRunSummaryView(taskRunsById[taskRunId], eventsByTaskRunId[taskRunId] ?? []),
        ]),
      ),
    [eventsByTaskRunId, taskRunIds, taskRunsById],
  )

  const loadSessionData = useCallback(async () => {
    if (!sessionId) return

    if (commandClient === null) {
      setLoadState(
        shouldWaitForRealtime(connectionStatus, authStatus, realtimeError, accessToken)
          ? 'loading'
          : 'error',
      )
      setErrorMessage(
        getRealtimeUnavailableMessage(connectionStatus, authStatus, realtimeError, accessToken),
      )
      return
    }

    setLoadState('loading')
    setErrorMessage(null)
    setActivityOpen(false)

    try {
      await Promise.all([fetchMessages(sessionId), fetchActiveTaskRuns(sessionId)])
      setLoadState('ready')
    } catch (error) {
      setLoadState('error')
      setErrorMessage(error instanceof Error ? error.message : '세션 메시지를 불러오지 못했습니다.')
    }
  }, [
    authStatus,
    commandClient,
    connectionStatus,
    accessToken,
    fetchActiveTaskRuns,
    fetchMessages,
    realtimeError,
    sessionId,
  ])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadSessionData()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadSessionData])

  useEffect(() => {
    hydratedTaskRunIdsRef.current.clear()
  }, [sessionId])

  useEffect(() => {
    if (commandClient === null || taskRunIds.length === 0) return

    taskRunIds.forEach((taskRunId) => {
      if (hydratedTaskRunIdsRef.current.has(taskRunId)) {
        return
      }

      hydratedTaskRunIdsRef.current.add(taskRunId)
      void fetchSnapshot(taskRunId).catch((error) => {
        setErrorMessage(
          error instanceof Error ? error.message : 'TaskRun 스냅샷 조회에 실패했습니다.',
        )
      })
      void replayEvents(taskRunId, lastSequenceByTaskRunId[taskRunId]).catch((error) => {
        setErrorMessage(
          error instanceof Error ? error.message : 'TaskRun 이벤트 조회에 실패했습니다.',
        )
      })

      if (socketClient !== null) {
        try {
          subscribeTask(taskRunId, lastSequenceByTaskRunId[taskRunId])
        } catch (error) {
          setErrorMessage(error instanceof Error ? error.message : 'TaskRun 구독에 실패했습니다.')
        }
      }
    })
  }, [
    commandClient,
    fetchSnapshot,
    lastSequenceByTaskRunId,
    replayEvents,
    socketClient,
    subscribeTask,
    taskRunIdKey,
    taskRunIds,
  ])

  const handleSend = async (content: string) => {
    if (!sessionId || isSending) return

    if (commandClient === null) {
      setLoadState(
        shouldWaitForRealtime(connectionStatus, authStatus, realtimeError, accessToken)
          ? 'loading'
          : 'error',
      )
      setErrorMessage(
        getRealtimeUnavailableMessage(connectionStatus, authStatus, realtimeError, accessToken),
      )
      return
    }

    setIsSending(true)
    setErrorMessage(null)
    try {
      await sendMessage({ sessionId, content })
      setLoadState('ready')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '메시지 전송에 실패했습니다.')
    } finally {
      setIsSending(false)
    }
  }

  const handleOpenTaskRun = (taskRunId: string) => {
    setSelectedTaskRunId(taskRunId)
    setActivityOpen(true)
  }

  const isComposerDisabled = connectionState === 'auth-expired' || commandClient === null
  const loading = loadState === 'loading' || isLoadingMessages
  const displayErrorMessage =
    errorMessage ?? (loadState === 'error' ? null : (chatError ?? taskRunError))

  return (
    <main className="bg-background flex min-w-0 flex-1 overflow-hidden">
      <section className="flex min-w-0 flex-1 flex-col">
        <ChatSessionHeader
          title={title}
          connectionState={connectionState}
          onOpenActivity={() => setActivityOpen(true)}
        />
        {displayErrorMessage && loadState !== 'error' && (
          <button
            type="button"
            onClick={() => setActivityOpen(true)}
            aria-label="오류 상세를 활동 패널에서 확인"
            className="border-border bg-muted/40 text-muted-foreground hover:text-foreground flex items-center justify-center gap-2 border-b px-4 py-2 text-xs transition-colors"
          >
            <AlertCircle className="h-3.5 w-3.5" />
            <span>{displayErrorMessage}</span>
          </button>
        )}
        {loading ? (
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
                onClick={() => void loadSessionData()}
                aria-label="세션 메시지 다시 불러오기"
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
            activitiesByTaskRunId={activitiesByTaskRunId}
            taskRunSummariesById={taskRunSummariesById}
            onOpenTaskRun={handleOpenTaskRun}
          />
        )}
        <ChatComposer disabled={isComposerDisabled} isSending={isSending} onSend={handleSend} />
      </section>
      <StepRunActivityPanel
        open={activityOpen}
        onOpenChange={setActivityOpen}
        sessionId={sessionId}
        selectedTaskRunId={selectedTaskRunId}
        onSelectTaskRun={setSelectedTaskRunId}
      />
    </main>
  )
}

function toChatConnectionState(
  connectionStatus: AiRealtimeConnectionStatus,
  authStatus: AiRealtimeAuthStatus,
): ChatConnectionState {
  if (authStatus === 'failed') {
    return 'auth-expired'
  }

  switch (connectionStatus) {
    case 'authenticated':
      return 'connected'
    case 'connecting':
    case 'open':
      return 'connecting'
    case 'reconnecting':
      return 'reconnecting'
    case 'error':
    case 'closed':
      return 'error'
    case 'idle':
    default:
      return 'idle'
  }
}

function isRealtimePending(connectionStatus: AiRealtimeConnectionStatus) {
  return (
    connectionStatus === 'connecting' ||
    connectionStatus === 'open' ||
    connectionStatus === 'reconnecting'
  )
}

function getRealtimeUnavailableMessage(
  connectionStatus: AiRealtimeConnectionStatus,
  authStatus: AiRealtimeAuthStatus,
  realtimeError: string | null,
  accessToken: string | null,
) {
  if (realtimeError !== null) {
    return realtimeError
  }
  if (authStatus === 'failed') {
    return '서버 인증이 만료되었거나 실패했습니다.'
  }
  if (accessToken === null || accessToken.trim() === '') {
    return '로그인이 필요합니다.'
  }
  if (shouldWaitForRealtime(connectionStatus, authStatus, realtimeError, accessToken)) {
    return '서버와 연결 중입니다. 잠시 후 다시 시도해 주세요.'
  }
  return '서버 연결을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

function shouldWaitForRealtime(
  connectionStatus: AiRealtimeConnectionStatus,
  authStatus: AiRealtimeAuthStatus,
  realtimeError: string | null,
  accessToken: string | null,
) {
  if (realtimeError !== null || authStatus === 'failed') {
    return false
  }
  if (accessToken === null || accessToken.trim() === '') {
    return false
  }
  return (
    isRealtimePending(connectionStatus) ||
    connectionStatus === 'idle' ||
    connectionStatus === 'closed'
  )
}
