import { useEffect, useRef, type ReactNode } from 'react'
import { refreshAccessToken } from '@/apis/auth'
import { createAiCommandClient } from '@/realtime/aiCommandClient'
import type { AiCommandClient } from '@/realtime/aiCommandClient'
import { getFramePayload, getStringField, isJsonObject } from '@/realtime/aiRealtimeTypes'
import { createTaskRunSocket, type TaskRunSocketClient } from '@/realtime/taskRunSocket'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'

type AiRealtimeProviderProps = {
  children: ReactNode
}

const PING_INTERVAL_MS = 25_000
const RECONNECT_DELAYS_MS = [1_000, 2_000, 5_000, 10_000, 30_000]

const getRecoveryLastSequence = (taskRunId: string) =>
  useTaskRunStore.getState().lastSequenceByTaskRunId[taskRunId]

export function AiRealtimeProvider({ children }: AiRealtimeProviderProps) {
  const accessToken = useAuthStore((state) => state.accessToken)
  const refreshToken = useAuthStore((state) => state.refreshToken)
  const setTokens = useAuthStore((state) => state.setTokens)
  const setSocketClient = useAiRealtimeStore((state) => state.setSocketClient)
  const setCommandClient = useAiRealtimeStore((state) => state.setCommandClient)
  const setConnectionStatus = useAiRealtimeStore((state) => state.setConnectionStatus)
  const setAuthStatus = useAiRealtimeStore((state) => state.setAuthStatus)
  const recordRawFrame = useAiRealtimeStore((state) => state.recordRawFrame)
  const setLastError = useAiRealtimeStore((state) => state.setLastError)
  const socketRef = useRef<TaskRunSocketClient | null>(null)
  const commandClientRef = useRef<AiCommandClient | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof window.setInterval> | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const manuallyClosedRef = useRef(false)
  const refreshAttemptedRef = useRef(false)
  const activeRecoveryInFlightRef = useRef(false)

  useEffect(() => {
    const clearPingInterval = () => {
      if (pingIntervalRef.current !== null) {
        window.clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
    }

    const clearReconnectTimeout = () => {
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    const cleanupClient = (closeSocket: boolean) => {
      clearPingInterval()
      commandClientRef.current?.destroy()
      commandClientRef.current = null
      setCommandClient(null)

      if (closeSocket) {
        socketRef.current?.close(1000, 'AI realtime provider cleanup')
      }
      socketRef.current = null
      setSocketClient(null)
    }

    const connect = (token: string) => {
      cleanupClient(true)
      setConnectionStatus(reconnectAttemptRef.current > 0 ? 'reconnecting' : 'connecting')
      setAuthStatus('authenticating')
      setLastError(null)

      const socketClient = createTaskRunSocket({ accessToken: token })
      const commandClient = createAiCommandClient(socketClient)
      socketRef.current = socketClient
      commandClientRef.current = commandClient
      setSocketClient(socketClient)
      setCommandClient(commandClient)

      socketClient.onOpen(() => {
        setConnectionStatus('open')
        clearPingInterval()
        pingIntervalRef.current = window.setInterval(() => {
          try {
            socketClient.ping()
          } catch (error) {
            setLastError(error instanceof Error ? error.message : 'AI WebSocket ping 실패')
          }
        }, PING_INTERVAL_MS)
      })

      socketClient.onRawMessage((frame) => {
        recordRawFrame(frame)
        useChatStore.getState().handleRealtimeFrame(frame)
        useTaskRunStore.getState().handleRealtimeFrame(frame)
        recoverTaskRunAfterGap(frame)
      })

      socketClient.onMessage((event) => {
        if (event.type === 'auth.ok') {
          refreshAttemptedRef.current = false
          reconnectAttemptRef.current = 0
          setAuthStatus('authenticated')
          setConnectionStatus('authenticated')
          void useChatStore
            .getState()
            .fetchSessions()
            .catch((error) => {
              setLastError(
                error instanceof Error ? error.message : '세션 목록 조회에 실패했습니다.',
              )
            })
          void recoverAndResubscribeTasks(socketClient)
          return
        }

        if (event.type === 'auth.failed' || event.type === 'auth.required') {
          setAuthStatus('failed')
          void refreshAndReconnect()
        }
      })

      socketClient.onClose(() => {
        clearPingInterval()
        commandClient.clearPending('AI WebSocket 연결이 닫혔습니다.')
        if (manuallyClosedRef.current) {
          setConnectionStatus('closed')
          return
        }
        scheduleReconnect()
      })

      socketClient.onError(() => {
        setConnectionStatus('error')
        setLastError('AI WebSocket 연결 오류가 발생했습니다.')
      })
    }

    const refreshAndReconnect = async () => {
      if (refreshToken === null || refreshAttemptedRef.current) {
        socketRef.current?.close(4001, 'AI auth failed')
        return
      }

      refreshAttemptedRef.current = true
      try {
        const response = await refreshAccessToken(refreshToken)
        setTokens(response.data.accessToken, response.data.refreshToken)
        connect(response.data.accessToken)
      } catch (error) {
        setLastError(error instanceof Error ? error.message : 'AI WebSocket 재인증에 실패했습니다.')
        socketRef.current?.close(4001, 'AI auth refresh failed')
      }
    }

    const scheduleReconnect = () => {
      if (accessToken === null || accessToken.trim() === '') {
        setConnectionStatus('closed')
        return
      }

      setConnectionStatus('reconnecting')
      const delay =
        RECONNECT_DELAYS_MS[Math.min(reconnectAttemptRef.current, RECONNECT_DELAYS_MS.length - 1)]
      reconnectAttemptRef.current += 1
      clearReconnectTimeout()
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect(accessToken)
      }, delay)
    }

    const recoverAndResubscribeTasks = async (socketClient: TaskRunSocketClient) => {
      if (activeRecoveryInFlightRef.current) {
        return
      }

      activeRecoveryInFlightRef.current = true

      try {
        let activeTaskRunIds: string[] = []
        try {
          activeTaskRunIds = (await useTaskRunStore.getState().fetchActiveTaskRuns()).map(
            (taskRun) => taskRun.task_run_id,
          )
        } catch (error) {
          setLastError(
            error instanceof Error ? error.message : '활성 TaskRun 목록 복구에 실패했습니다.',
          )
        }

        if (socketRef.current !== socketClient || !socketClient.isAuthenticated()) {
          return
        }

        const subscriptionIds = Object.values(
          useAiRealtimeStore.getState().subscriptionsByTaskRunId,
        ).map((subscription) => subscription.task_run_id)
        const taskRunIds = Array.from(new Set([...subscriptionIds, ...activeTaskRunIds]))

        for (const taskRunId of taskRunIds) {
          try {
            await useTaskRunStore.getState().recoverTaskRun(taskRunId)

            if (socketRef.current !== socketClient || !socketClient.isAuthenticated()) {
              return
            }

            useAiRealtimeStore
              .getState()
              .subscribeTask(taskRunId, getRecoveryLastSequence(taskRunId), { force: true })
          } catch (error) {
            setLastError(error instanceof Error ? error.message : 'TaskRun 재구독에 실패했습니다.')
          }
        }
      } finally {
        activeRecoveryInFlightRef.current = false
      }
    }

    const recoverTaskRunAfterGap = (frame: { type: string; payload?: unknown; data?: unknown }) => {
      if (frame.type !== 'task.event') {
        return
      }

      const payload = getFramePayload(frame)
      if (!isJsonObject(payload)) {
        return
      }

      const taskRunId = getStringField(payload, 'task_run_id', 'taskRunId')
      if (
        taskRunId === undefined ||
        useTaskRunStore.getState().replayNeededByTaskRunId[taskRunId] !== true
      ) {
        return
      }

      void useTaskRunStore
        .getState()
        .recoverTaskRun(taskRunId)
        .then(() => {
          const currentSocketClient = socketRef.current
          if (currentSocketClient === null || !currentSocketClient.isAuthenticated()) {
            return
          }
          useAiRealtimeStore.getState().subscribeTask(taskRunId, getRecoveryLastSequence(taskRunId))
        })
        .catch((error) => {
          setLastError(
            error instanceof Error ? error.message : 'TaskRun 이벤트 복구에 실패했습니다.',
          )
        })
    }

    manuallyClosedRef.current = false
    clearReconnectTimeout()

    if (accessToken === null || accessToken.trim() === '') {
      manuallyClosedRef.current = true
      cleanupClient(true)
      setConnectionStatus('idle')
      setAuthStatus('anonymous')
      return () => {
        clearReconnectTimeout()
        cleanupClient(true)
      }
    }

    connect(accessToken)

    return () => {
      manuallyClosedRef.current = true
      clearReconnectTimeout()
      cleanupClient(true)
    }
  }, [
    accessToken,
    refreshToken,
    recordRawFrame,
    setAuthStatus,
    setCommandClient,
    setConnectionStatus,
    setLastError,
    setSocketClient,
    setTokens,
  ])

  return children
}
