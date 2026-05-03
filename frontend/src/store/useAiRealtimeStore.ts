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

export const useAiRealtimeStore = create<AiRealtimeState>((set, get) => ({
  connectionStatus: 'idle',
  authStatus: 'anonymous',
  socketClient: null,
  commandClient: null,
  rawFrames: [],
  subscriptionsByTaskRunId: {},
  lastError: null,
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setAuthStatus: (status) => set({ authStatus: status }),
  setSocketClient: (client) => set({ socketClient: client }),
  setCommandClient: (client) => set({ commandClient: client }),
  recordRawFrame: (frame) =>
    set((state) => ({
      rawFrames: [...state.rawFrames, frame].slice(-MAX_RAW_FRAMES),
    })),
  setLastError: (message) => set({ lastError: message }),
  sendCommand: (type, payload) => {
    const commandClient = get().commandClient
    if (commandClient === null) {
      return Promise.reject(new Error('AI realtime command client가 아직 준비되지 않았습니다.'))
    }
    return commandClient.sendCommand(type, payload)
  },
  subscribeTask: (taskRunId, lastSequence, options = {}) => {
    const socketClient = get().socketClient
    if (socketClient === null) {
      throw new Error('AI WebSocket client가 아직 준비되지 않았습니다.')
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
      socketClient: null,
      commandClient: null,
      rawFrames: [],
      subscriptionsByTaskRunId: {},
      lastError: null,
    })
  },
}))
