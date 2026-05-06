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
import {
  isInternalStepAnchorEvent,
  isInternalStepAnchorStepRun,
  isLiveTaskRunStatus,
  toActivityItemView,
  toTaskRunSummaryView,
} from '@/utils/taskRunStatusView'

type LoadState = 'loading' | 'ready' | 'error'

const EMPTY_MESSAGES: never[] = []

export function ChatSessionPage() {
  const { sessionId = '' } = useParams()
  const [activityOpen, setActivityOpen] = useState(false)
  const [selectedTaskRunId, setSelectedTaskRunId] = useState<string | undefined>()
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [focusedTaskRunTarget, setFocusedTaskRunTarget] = useState<
    { taskRunId: string; requestId: number } | undefined
  >()
  const focusRequestIdRef = useRef(0)
  const hydratedTaskRunIdsRef = useRef<Set<string>>(new Set())
  const hydratingTaskRunIdsRef = useRef<Set<string>>(new Set())
  const hydrationGenerationRef = useRef(0)
  const loadGenerationRef = useRef(0)

  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const socketClient = useAiRealtimeStore((state) => state.socketClient)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const authenticatedReady = useAiRealtimeStore((state) => state.authenticatedReady)
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
  const currentSession = useChatStore((state) =>
    sessionId === '' ? undefined : state.sessionsById[sessionId],
  )
  const fetchMessages = useChatStore((state) => state.fetchMessages)
  const sendMessage = useChatStore((state) => state.sendMessage)

  const taskRunsById = useTaskRunStore((state) => state.taskRunsById)
  const stepRunsById = useTaskRunStore((state) => state.stepRunsById)
  const eventsByTaskRunId = useTaskRunStore((state) => state.eventsByTaskRunId)
  const lastSequenceByTaskRunId = useTaskRunStore((state) => state.lastSequenceByTaskRunId)
  const taskRunError = useTaskRunStore((state) => state.lastError)
  const fetchActiveTaskRuns = useTaskRunStore((state) => state.fetchActiveTaskRuns)
  const fetchSnapshot = useTaskRunStore((state) => state.fetchSnapshot)
  const replayEvents = useTaskRunStore((state) => state.replayEvents)

  const connectionState = useMemo(
    () => toChatConnectionState(connectionStatus, authStatus),
    [authStatus, connectionStatus],
  )
  const messages = useMemo(
    () =>
      storeMessages.filter((message) => message.role === 'user' || message.role === 'assistant'),
    [storeMessages],
  )
  const title = useMemo(() => {
    const sessionTitle = getNonEmptyString(currentSession?.title)
    if (sessionTitle !== undefined) {
      return sessionTitle
    }

    const preview =
      getNonEmptyString(currentSession?.last_message) ??
      getNonEmptyString(messages.find((message) => message.role === 'user')?.content)

    return preview ?? '새 대화'
  }, [currentSession?.last_message, currentSession?.title, messages])
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
          (eventsByTaskRunId[taskRunId] ?? [])
            .filter((event) => !isInternalStepAnchorEvent(event))
            .map(toActivityItemView),
        ]),
      ),
    [eventsByTaskRunId, taskRunIds],
  )
  const stepRunsByTaskRunId = useMemo(
    () =>
      Object.fromEntries(
        taskRunIds.map((taskRunId) => [
          taskRunId,
          Object.values(stepRunsById)
            .filter((stepRun) => stepRun.task_run_id === taskRunId)
            .filter((stepRun) => !isInternalStepAnchorStepRun(stepRun))
            .sort(compareChatStepRuns),
        ]),
      ),
    [stepRunsById, taskRunIds],
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
  const isPendingSession = sessionId.startsWith('pending_session_')

  const loadSessionData = useCallback(async () => {
    if (!sessionId) return
    if (isPendingSession) {
      // 첫 메시지 전송 직후에는 서버 세션 id가 아직 없어서 조회 명령을 보내지 않는다.
      // optimistic 메시지가 들어간 pending 세션을 그대로 렌더링하고 accepted 후 실제 세션으로 교체한다.
      setLoadState('ready')
      setErrorMessage(null)
      return
    }

    if (!authenticatedReady || commandClient === null) {
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

    const loadGeneration = ++loadGenerationRef.current
    const requestedSessionId = sessionId

    setLoadState('loading')
    setErrorMessage(null)
    setActivityOpen(false)

    try {
      await Promise.all([
        fetchMessages(requestedSessionId),
        fetchActiveTaskRuns(requestedSessionId),
      ])
      if (loadGeneration !== loadGenerationRef.current || requestedSessionId !== sessionId) {
        return
      }
      setLoadState('ready')
    } catch (error) {
      if (loadGeneration !== loadGenerationRef.current || requestedSessionId !== sessionId) {
        return
      }
      setLoadState('error')
      setErrorMessage(error instanceof Error ? error.message : '세션 메시지를 불러오지 못했습니다.')
    }
  }, [
    authStatus,
    authenticatedReady,
    commandClient,
    connectionStatus,
    accessToken,
    fetchActiveTaskRuns,
    fetchMessages,
    isPendingSession,
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
    loadGenerationRef.current += 1
    hydrationGenerationRef.current += 1
    hydratedTaskRunIdsRef.current.clear()
    hydratingTaskRunIdsRef.current.clear()
  }, [sessionId])

  useEffect(() => {
    if (
      !authenticatedReady ||
      commandClient === null ||
      socketClient === null ||
      taskRunIds.length === 0
    ) {
      return
    }

    const hydrationGeneration = hydrationGenerationRef.current
    let cancelled = false

    taskRunIds.forEach((taskRunId) => {
      if (
        hydratedTaskRunIdsRef.current.has(taskRunId) ||
        hydratingTaskRunIdsRef.current.has(taskRunId)
      ) {
        return
      }

      const taskRun = taskRunsById[taskRunId]
      const taskRunEvents = eventsByTaskRunId[taskRunId] ?? []
      const latestTaskRunEvent = taskRunEvents.at(-1)
      const latestTaskRunStatus =
        latestTaskRunEvent?.status ?? latestTaskRunEvent?.event_type ?? taskRun?.status
      const hasStreamingMessage = messages.some(
        (message) =>
          message.taskRunId === taskRunId &&
          message.role === 'assistant' &&
          message.status === 'streaming',
      )
      const hasRuntimeState =
        taskRun !== undefined || taskRunEvents.length > 0 || hasStreamingMessage

      if (!hasRuntimeState) {
        // 과거 완료 메시지까지 모두 snapshot/replay 하면 WebSocket command가 폭주해서
        // 현재 답변의 step event가 뒤로 밀린다. 완료 이력은 활동 패널을 열 때 lazy load한다.
        return
      }

      if (hasStreamingMessage || isLiveTaskRunStatus(latestTaskRunStatus)) {
        try {
          // 실행 중인 답변은 snapshot command로 UI를 막지 않고 live event 구독만 유지한다.
          subscribeTask(taskRunId, lastSequenceByTaskRunId[taskRunId])
        } catch (error) {
          console.error(error)
        }
        return
      }

      hydratingTaskRunIdsRef.current.add(taskRunId)
      // snapshot/replay merge는 store를 갱신해서 이 effect를 다시 실행시킬 수 있다.
      // 그래서 요청 성공 뒤가 아니라 시작 시점에 먼저 표시해 같은 taskRunId 중복 조회를 막는다.
      hydratedTaskRunIdsRef.current.add(taskRunId)
      void (async () => {
        try {
          const snapshot = await fetchSnapshot(taskRunId)
          const hydratedTaskRun = useTaskRunStore.getState().taskRunsById[taskRunId]
          if (
            cancelled ||
            hydrationGeneration !== hydrationGenerationRef.current ||
            (hydratedTaskRun?.session_id !== undefined && hydratedTaskRun.session_id !== sessionId)
          ) {
            return
          }
          const snapshotHasEvents = Array.isArray(snapshot?.events) && snapshot.events.length > 0
          if (!snapshotHasEvents) {
            // snapshot이 event 목록을 함께 주는 경우에는 replay를 한 번 더 호출하지 않는다.
            // 완료 직후 agent loop가 아직 정리 중이면 replay command 응답이 늦어져 콘솔 timeout이 생길 수 있다.
            await replayEvents(taskRunId, lastSequenceByTaskRunId[taskRunId])
          }
          if (
            cancelled ||
            hydrationGeneration !== hydrationGenerationRef.current ||
            !useAiRealtimeStore.getState().authenticatedReady
          ) {
            return
          }
          // replay/snapshot merge가 끝난 뒤 store의 최신 sequence를 다시 읽어야
          // 구독 기준점이 오래된 closure 값에 묶이지 않는다.
          const latestSequence = useTaskRunStore.getState().lastSequenceByTaskRunId[taskRunId]
          subscribeTask(taskRunId, latestSequence)
          hydratedTaskRunIdsRef.current.add(taskRunId)
        } catch (error) {
          if (cancelled || hydrationGeneration !== hydrationGenerationRef.current) {
            return
          }
          console.error(error)
          hydratedTaskRunIdsRef.current.delete(taskRunId)
          setErrorMessage('답변 진행 상태를 불러오지 못했습니다.')
        } finally {
          hydratingTaskRunIdsRef.current.delete(taskRunId)
        }
      })()
    })

    return () => {
      cancelled = true
    }
  }, [
    authenticatedReady,
    commandClient,
    eventsByTaskRunId,
    fetchSnapshot,
    lastSequenceByTaskRunId,
    messages,
    replayEvents,
    sessionId,
    socketClient,
    subscribeTask,
    taskRunIdKey,
    taskRunIds,
    taskRunsById,
  ])

  const handleSend = async (content: string) => {
    if (!sessionId || isSending) return

    if (!authenticatedReady || commandClient === null) {
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

  const handleFocusTaskRunMessage = (taskRunId: string) => {
    focusRequestIdRef.current += 1
    setFocusedTaskRunTarget({ taskRunId, requestId: focusRequestIdRef.current })
  }

  const activeSessionTaskRunId =
    typeof currentSession?.active_task_run_id === 'string'
      ? currentSession.active_task_run_id
      : undefined
  const hasActiveChatTurn =
    activeSessionTaskRunId !== undefined ||
    messages.some(
      (message) =>
        message.status === 'optimistic' ||
        message.status === 'streaming' ||
        message.status === 'waiting',
    )
  const isStreaming = messages.some(
    (message) => message.role === 'assistant' && message.status === 'streaming',
  )
  const isComposerDisabled =
    connectionState === 'auth-expired' ||
    !authenticatedReady ||
    commandClient === null ||
    hasActiveChatTurn
  const loading = (loadState === 'loading' || isLoadingMessages) && messages.length === 0
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
        ) : loadState === 'error' && messages.length === 0 ? (
          <div className="flex min-h-0 flex-1 items-center justify-center px-6">
            <div className="border-border bg-card max-w-md rounded-lg border p-5 text-center shadow-sm">
              <AlertCircle className="text-destructive mx-auto h-6 w-6" />
              <h2 className="text-foreground mt-3 text-sm font-semibold">
                대화를 불러오지 못했습니다
              </h2>
              <p className="text-muted-foreground mt-2 text-sm leading-6">{errorMessage}</p>
              <button
                type="button"
                onClick={() => void loadSessionData()}
                aria-label="대화 메시지 다시 불러오기"
                className="bg-primary text-primary-foreground hover:bg-primary/90 mt-4 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
              >
                <RefreshCw className="h-4 w-4" />
                다시 시도
              </button>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <ChatEmptyState />
        ) : (
          <ChatMessageList
            messages={messages}
            activitiesByTaskRunId={activitiesByTaskRunId}
            stepRunsByTaskRunId={stepRunsByTaskRunId}
            taskRunSummariesById={taskRunSummariesById}
            onOpenTaskRun={handleOpenTaskRun}
            focusedTaskRunTarget={focusedTaskRunTarget}
          />
        )}
        <ChatComposer
          disabled={isComposerDisabled}
          isSending={isSending || isStreaming}
          onSend={handleSend}
        />
      </section>
      <StepRunActivityPanel
        open={activityOpen}
        onOpenChange={setActivityOpen}
        sessionId={sessionId}
        selectedTaskRunId={selectedTaskRunId}
        onSelectTaskRun={setSelectedTaskRunId}
        onFocusTaskRunMessage={handleFocusTaskRunMessage}
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

const compareChatStepRuns = (
  first: { step_order?: number | null; stepOrder?: number | null; sequence?: number | null },
  second: { step_order?: number | null; stepOrder?: number | null; sequence?: number | null },
) => {
  const firstOrder = getChatStepOrder(first)
  const secondOrder = getChatStepOrder(second)
  if (firstOrder !== undefined && secondOrder !== undefined) {
    return firstOrder - secondOrder
  }
  return (first.sequence ?? 0) - (second.sequence ?? 0)
}

const getChatStepOrder = (stepRun: { step_order?: number | null; stepOrder?: number | null }) => {
  if (typeof stepRun.step_order === 'number' && Number.isFinite(stepRun.step_order)) {
    return stepRun.step_order
  }
  if (typeof stepRun.stepOrder === 'number' && Number.isFinite(stepRun.stepOrder)) {
    return stepRun.stepOrder
  }
  return undefined
}

function getNonEmptyString(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : undefined
}
