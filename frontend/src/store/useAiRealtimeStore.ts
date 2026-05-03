import { create } from 'zustand'
import type { AiCommandClient } from '@/realtime/aiCommandClient'
import type {
  AiRealtimeAuthStatus,
  AiRealtimeCommandPayloadMap,
  AiRealtimeCommandType,
  AiRealtimeConnectionStatus,
  AiRealtimeRawFrame,
} from '@/realtime/aiRealtimeTypes'
import type { TaskRunSocketClient } from '@/realtime/taskRunSocket'

export type AiRealtimeSubscription = {
  task_run_id: string
  last_sequence?: number
  subscribed_at?: string
}

type AiRealtimeState = {
  connectionStatus: AiRealtimeConnectionStatus
  authStatus: AiRealtimeAuthStatus
  authenticatedReady: boolean
  socketClient: TaskRunSocketClient | null
  commandClient: AiCommandClient | null
  rawFrames: AiRealtimeRawFrame[]
  subscriptionsByTaskRunId: Record<string, AiRealtimeSubscription>
  lastError: string | null
  setConnectionStatus: (status: AiRealtimeConnectionStatus) => void
  setAuthStatus: (status: AiRealtimeAuthStatus) => void
  setSocketClient: (client: TaskRunSocketClient | null) => void
  setCommandClient: (client: AiCommandClient | null) => void
  recordRawFrame: (frame: AiRealtimeRawFrame) => void
  setLastError: (message: string | null) => void
  sendCommand: <TResult = unknown, TType extends AiRealtimeCommandType = AiRealtimeCommandType>(
    type: TType,
    payload: AiRealtimeCommandPayloadMap[TType],
  ) => Promise<TResult>
  subscribeTask: (taskRunId: string, lastSequence?: number, options?: { force?: boolean }) => void
  resetRealtimeState: () => void
}

const MAX_RAW_FRAMES = 200

const getAuthenticatedReady = (
  state: Pick<AiRealtimeState, 'authStatus' | 'socketClient' | 'commandClient'>,
) =>
  state.authStatus === 'authenticated' &&
  state.socketClient !== null &&
  state.commandClient !== null &&
  state.socketClient.isAuthenticated()

export const useAiRealtimeStore = create<AiRealtimeState>((set, get) => ({
  connectionStatus: 'idle',
  authStatus: 'anonymous',
  authenticatedReady: false,
  socketClient: null,
  commandClient: null,
  rawFrames: [],
  subscriptionsByTaskRunId: {},
  lastError: null,
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setAuthStatus: (authStatus) =>
    set((state) => ({
      authStatus,
      authenticatedReady: getAuthenticatedReady({ ...state, authStatus }),
    })),
  setSocketClient: (socketClient) =>
    set((state) => ({
      socketClient,
      authenticatedReady: getAuthenticatedReady({ ...state, socketClient }),
    })),
  setCommandClient: (commandClient) =>
    set((state) => ({
      commandClient,
      authenticatedReady: getAuthenticatedReady({ ...state, commandClient }),
    })),
  recordRawFrame: (frame) =>
    set((state) => ({
      rawFrames: [...state.rawFrames, frame].slice(-MAX_RAW_FRAMES),
    })),
  setLastError: (message) => set({ lastError: message }),
  sendCommand: (type, payload) => {
    const { authenticatedReady, commandClient } = get()
    if (!authenticatedReady) {
      return Promise.reject(new Error('AI WebSocket 인증이 완료된 뒤 다시 시도해 주세요.'))
    }
    if (commandClient === null) {
      return Promise.reject(new Error('AI realtime command client가 아직 준비되지 않았습니다.'))
    }
    return commandClient.sendCommand(type, payload)
  },
  subscribeTask: (taskRunId, lastSequence, options = {}) => {
    const { authStatus, socketClient } = get()
    if (socketClient === null) {
      throw new Error('AI WebSocket client가 아직 준비되지 않았습니다.')
    }
    if (authStatus !== 'authenticated' || !socketClient.isAuthenticated()) {
      throw new Error('AI WebSocket 인증 완료 전에는 구독할 수 없습니다.')
    }

    const current = get().subscriptionsByTaskRunId[taskRunId]
    if (options.force !== true && current !== undefined && current.last_sequence === lastSequence) {
      return
    }

    socketClient.subscribeTask(taskRunId, { lastSequence })
    set((state) => ({
      subscriptionsByTaskRunId: {
        ...state.subscriptionsByTaskRunId,
        [taskRunId]: {
          task_run_id: taskRunId,
          last_sequence: lastSequence,
          subscribed_at: new Date().toISOString(),
        },
      },
    }))
  },
  resetRealtimeState: () => {
    const { commandClient, socketClient } = get()
    commandClient?.clearPending('AI realtime 상태가 초기화되었습니다.')
    socketClient?.close(1000, 'AI realtime reset')
    set({
      connectionStatus: 'idle',
      authStatus: 'anonymous',
      authenticatedReady: false,
      socketClient: null,
      commandClient: null,
      rawFrames: [],
      subscriptionsByTaskRunId: {},
      lastError: null,
    })
  },
}))
