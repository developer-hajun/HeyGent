import { create } from 'zustand'
import {
  type AiRealtimeRawFrame,
  type RawTaskEventPayload,
  getFramePayload,
  getStringField,
  isJsonObject,
} from '@/realtime/aiRealtimeTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import type {
  RawApproval,
  RawStepRun,
  RawTaskRun,
  RawTaskRunSnapshot,
  TaskRunEventsReplayResultPayload,
  TaskRunsActiveListResultPayload,
} from '@/types/taskRuns'
import { createApprovalResponseId, createClientCommandId } from '@/utils/requestId'
import { getLastTaskRunSequence, mergeTaskRunEvents } from '@/utils/taskRunEvents'

type TaskRunState = {
  taskRunsById: Record<string, RawTaskRun>
  stepRunsById: Record<string, RawStepRun>
  approvalsById: Record<string, RawApproval>
  eventsByTaskRunId: Record<string, RawTaskEventPayload[]>
  lastSequenceByTaskRunId: Record<string, number>
  replayNeededByTaskRunId: Record<string, boolean>
  lastError: string | null
  fetchActiveTaskRuns: (sessionId?: string) => Promise<RawTaskRun[]>
  fetchSnapshot: (taskRunId: string) => Promise<RawTaskRunSnapshot | null>
  replayEvents: (taskRunId: string, afterSequence?: number) => Promise<RawTaskEventPayload[]>
  resumeTaskRun: (input: {
    taskRunId: string
    approvalId?: string
    decision?: string
    response?: unknown
  }) => Promise<AiRealtimeRawFrame>
  cancelTaskRun: (taskRunId: string, reason?: string) => Promise<AiRealtimeRawFrame>
  handleRealtimeFrame: (frame: AiRealtimeRawFrame) => void
  mergeTaskEvent: (event: RawTaskEventPayload) => void
  clearTaskRunState: () => void
}

export const useTaskRunStore = create<TaskRunState>((set, get) => ({
  taskRunsById: {},
  stepRunsById: {},
  approvalsById: {},
  eventsByTaskRunId: {},
  lastSequenceByTaskRunId: {},
  replayNeededByTaskRunId: {},
  lastError: null,
  fetchActiveTaskRuns: async (sessionId) => {
    const frame = await useAiRealtimeStore
      .getState()
      .sendCommand<AiRealtimeRawFrame>('taskRuns.active.list', { sessionId })
    const taskRuns = getRawTaskRunList(getFramePayload(frame))
    mergeTaskRuns(taskRuns, set)
    return taskRuns
  },
  fetchSnapshot: async (taskRunId) => {
    const frame = await useAiRealtimeStore
      .getState()
      .sendCommand<AiRealtimeRawFrame>('taskRun.snapshot.get', { taskRunId })
    const snapshot = getFramePayload(frame) as RawTaskRunSnapshot | undefined
    if (!isJsonObject(snapshot)) {
      return null
    }

    mergeSnapshot(snapshot, set)
    return snapshot
  },
  replayEvents: async (taskRunId, afterSequence) => {
    const frame = await useAiRealtimeStore
      .getState()
      .sendCommand<AiRealtimeRawFrame>('taskRun.events.replay', { taskRunId, afterSequence })
    const payload = getFramePayload(frame) as TaskRunEventsReplayResultPayload
    const events = getRawTaskEventList(payload)

    set((state) => {
      const currentEvents = state.eventsByTaskRunId[taskRunId] ?? []
      const mergeResult = mergeTaskRunEvents(currentEvents, events)
      return {
        eventsByTaskRunId: {
          ...state.eventsByTaskRunId,
          [taskRunId]: mergeResult.events,
        },
        lastSequenceByTaskRunId:
          mergeResult.lastSequence === undefined
            ? state.lastSequenceByTaskRunId
            : {
                ...state.lastSequenceByTaskRunId,
                [taskRunId]: mergeResult.lastSequence,
              },
        replayNeededByTaskRunId: {
          ...state.replayNeededByTaskRunId,
          [taskRunId]: payload.retention_exceeded === true || payload.retentionExceeded === true,
        },
      }
    })

    return events
  },
  resumeTaskRun: (input) =>
    useAiRealtimeStore.getState().sendCommand<AiRealtimeRawFrame>('taskRun.resume', {
      taskRunId: input.taskRunId,
      approvalId: input.approvalId,
      approvalResponseId: createApprovalResponseId(),
      decision: input.decision,
      response: input.response,
    }),
  cancelTaskRun: (taskRunId, reason) =>
    useAiRealtimeStore.getState().sendCommand<AiRealtimeRawFrame>('taskRun.cancel', {
      taskRunId,
      clientCommandId: createClientCommandId(),
      reason,
    }),
  handleRealtimeFrame: (frame) => {
    switch (frame.type) {
      case 'task.event': {
        const payload = getFramePayload(frame)
        if (isRawTaskEventPayload(payload)) {
          get().mergeTaskEvent(payload)
        }
        return
      }
      case 'taskRuns.active.list.result':
        mergeTaskRuns(getRawTaskRunList(getFramePayload(frame)), set)
        return
      case 'taskRun.snapshot.result': {
        const snapshot = getFramePayload(frame)
        if (isJsonObject(snapshot)) {
          mergeSnapshot(snapshot, set)
        }
        return
      }
      case 'taskRun.events.replay.result': {
        const payload = getFramePayload(frame)
        if (isJsonObject(payload)) {
          const taskRunId = getStringField(payload, 'task_run_id', 'taskRunId')
          const events = getRawTaskEventList(payload)
          if (taskRunId !== undefined) {
            mergeReplayResult(taskRunId, events, payload, set)
          }
        }
        return
      }
      default:
        return
    }
  },
  mergeTaskEvent: (event) => {
    set((state) => {
      const currentEvents = state.eventsByTaskRunId[event.task_run_id] ?? []
      const mergeResult = mergeTaskRunEvents(currentEvents, [event])

      return {
        eventsByTaskRunId: {
          ...state.eventsByTaskRunId,
          [event.task_run_id]: mergeResult.events,
        },
        lastSequenceByTaskRunId:
          mergeResult.lastSequence === undefined
            ? state.lastSequenceByTaskRunId
            : {
                ...state.lastSequenceByTaskRunId,
                [event.task_run_id]: mergeResult.lastSequence,
              },
        replayNeededByTaskRunId: {
          ...state.replayNeededByTaskRunId,
          [event.task_run_id]:
            state.replayNeededByTaskRunId[event.task_run_id] === true || mergeResult.hasGap,
        },
      }
    })
  },
  clearTaskRunState: () =>
    set({
      taskRunsById: {},
      stepRunsById: {},
      approvalsById: {},
      eventsByTaskRunId: {},
      lastSequenceByTaskRunId: {},
      replayNeededByTaskRunId: {},
      lastError: null,
    }),
}))

const getRawTaskRunList = (payload: TaskRunsActiveListResultPayload | unknown): RawTaskRun[] => {
  if (!isJsonObject(payload)) {
    return []
  }

  const list = Array.isArray(payload.task_runs)
    ? payload.task_runs
    : Array.isArray(payload.taskRuns)
      ? payload.taskRuns
      : Array.isArray(payload.items)
        ? payload.items
        : []

  return list.filter(isRawTaskRun)
}

const getRawTaskEventList = (payload: TaskRunEventsReplayResultPayload | unknown) => {
  if (!isJsonObject(payload) || !Array.isArray(payload.events)) {
    return []
  }
  return payload.events.filter(isRawTaskEventPayload)
}

const mergeTaskRuns = (
  taskRuns: RawTaskRun[],
  set: (partial: Partial<TaskRunState> | ((state: TaskRunState) => Partial<TaskRunState>)) => void,
) => {
  set((state) => ({
    taskRunsById: {
      ...state.taskRunsById,
      ...Object.fromEntries(taskRuns.map((taskRun) => [taskRun.task_run_id, taskRun])),
    },
  }))
}

const mergeSnapshot = (
  snapshot: RawTaskRunSnapshot,
  set: (partial: Partial<TaskRunState> | ((state: TaskRunState) => Partial<TaskRunState>)) => void,
) => {
  const taskRun = (snapshot.task_run ?? snapshot.taskRun) as RawTaskRun | undefined
  const stepRuns = (snapshot.step_runs ?? snapshot.stepRuns ?? []).filter(isRawStepRun)
  const approvals = (snapshot.approvals ?? []).filter(isRawApproval)
  const events = (snapshot.events ?? []).filter(isRawTaskEventPayload)

  set((state) => {
    const nextEventsByTaskRunId = { ...state.eventsByTaskRunId }
    const nextLastSequenceByTaskRunId = { ...state.lastSequenceByTaskRunId }

    events.forEach((event) => {
      const mergeResult = mergeTaskRunEvents(nextEventsByTaskRunId[event.task_run_id] ?? [], [
        event,
      ])
      nextEventsByTaskRunId[event.task_run_id] = mergeResult.events
      const lastSequence = getLastTaskRunSequence(mergeResult.events)
      if (lastSequence !== undefined) {
        nextLastSequenceByTaskRunId[event.task_run_id] = lastSequence
      }
    })

    return {
      taskRunsById:
        taskRun === undefined
          ? state.taskRunsById
          : { ...state.taskRunsById, [taskRun.task_run_id]: taskRun },
      stepRunsById: {
        ...state.stepRunsById,
        ...Object.fromEntries(stepRuns.map((stepRun) => [stepRun.step_run_id, stepRun])),
      },
      approvalsById: {
        ...state.approvalsById,
        ...Object.fromEntries(approvals.map((approval) => [approval.approval_id, approval])),
      },
      eventsByTaskRunId: nextEventsByTaskRunId,
      lastSequenceByTaskRunId: nextLastSequenceByTaskRunId,
    }
  })
}

const mergeReplayResult = (
  taskRunId: string,
  events: RawTaskEventPayload[],
  payload: Record<string, unknown>,
  set: (partial: Partial<TaskRunState> | ((state: TaskRunState) => Partial<TaskRunState>)) => void,
) => {
  set((state) => {
    const mergeResult = mergeTaskRunEvents(state.eventsByTaskRunId[taskRunId] ?? [], events)
    return {
      eventsByTaskRunId: {
        ...state.eventsByTaskRunId,
        [taskRunId]: mergeResult.events,
      },
      lastSequenceByTaskRunId:
        mergeResult.lastSequence === undefined
          ? state.lastSequenceByTaskRunId
          : {
              ...state.lastSequenceByTaskRunId,
              [taskRunId]: mergeResult.lastSequence,
            },
      replayNeededByTaskRunId: {
        ...state.replayNeededByTaskRunId,
        [taskRunId]: payload.retention_exceeded === true || payload.retentionExceeded === true,
      },
    }
  })
}

const isRawTaskRun = (value: unknown): value is RawTaskRun =>
  isJsonObject(value) && typeof value.task_run_id === 'string'

const isRawStepRun = (value: unknown): value is RawStepRun =>
  isJsonObject(value) &&
  typeof value.step_run_id === 'string' &&
  typeof value.task_run_id === 'string'

const isRawApproval = (value: unknown): value is RawApproval =>
  isJsonObject(value) &&
  typeof value.approval_id === 'string' &&
  typeof value.task_run_id === 'string'

const isRawTaskEventPayload = (value: unknown): value is RawTaskEventPayload =>
  isJsonObject(value) &&
  typeof value.event_id === 'string' &&
  typeof value.event_type === 'string' &&
  typeof value.task_run_id === 'string'
