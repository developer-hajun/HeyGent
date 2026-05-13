import { X } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { RawStepRun, RawTaskRun } from '@/types/taskRuns'
import {
  isInternalStepAnchorEvent,
  isInternalStepAnchorStepRun,
  isLiveTaskRunStatus,
  toActivityItemView,
  toTaskRunSummaryView,
} from '@/utils/taskRunStatusView'
import { findPromptForTaskRun, getTime } from './activityPanelText'
import { SelectedTaskRunView } from './SelectedTaskRunView'
import { TaskRunSummaryList } from './TaskRunSummaryList'

const EMPTY_MESSAGES: never[] = []

export function StepRunActivityPanelBody({
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
  onFocusTaskRunMessage,
  onClose,
}: {
  sessionId: string
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string | undefined) => void
  onFocusTaskRunMessage?: (taskRunId: string) => void
  onClose: () => void
}) {
  const loadedTaskRunIdsRef = useRef<Set<string>>(new Set())
  const memoryObservationRefreshIdsRef = useRef<Set<string>>(new Set())
  const messages = useChatStore((state) =>
    sessionId === '' ? EMPTY_MESSAGES : (state.messagesBySessionId[sessionId] ?? EMPTY_MESSAGES),
  )
  const taskRunsById = useTaskRunStore((state) => state.taskRunsById)
  const stepRunsById = useTaskRunStore((state) => state.stepRunsById)
  const approvalsById = useTaskRunStore((state) => state.approvalsById)
  const eventsByTaskRunId = useTaskRunStore((state) => state.eventsByTaskRunId)
  const replayNeededByTaskRunId = useTaskRunStore((state) => state.replayNeededByTaskRunId)
  const fetchSnapshot = useTaskRunStore((state) => state.fetchSnapshot)
  const replayEvents = useTaskRunStore((state) => state.replayEvents)

  // 메시지에 먼저 붙은 taskRunId와 snapshot/replay로 뒤늦게 들어온 TaskRun을 함께 모은다.
  // 이렇게 해야 첫 응답 직후와 새로고침 복구 직후가 같은 목록 규칙을 쓴다.
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

    collectLinkedTaskRunIds(ids, eventsByTaskRunId)

    return [...ids]
  }, [eventsByTaskRunId, messages, sessionId, taskRunsById])

  const taskRunSummaries = useMemo(
    () =>
      taskRunIds
        .map((taskRunId) => {
          const summary = toTaskRunSummaryView(
            taskRunsById[taskRunId],
            eventsByTaskRunId[taskRunId] ?? [],
          )
          // 새로고침 직후에는 메시지에 taskRunId만 있고 snapshot은 아직 없을 수 있다.
          // 이때 summary id를 unknown으로 두면 panel lazy load가 잘못된 taskRunId로 요청된다.
          return summary.id === 'unknown' ? { ...summary, id: taskRunId } : summary
        })
        .sort((first, second) => (second.lastSequence ?? 0) - (first.lastSequence ?? 0)),
    [eventsByTaskRunId, taskRunIds, taskRunsById],
  )

  // 외부에서 선택된 값이 현재 대화의 진행 기록이 아니면, 가장 최근 sequence의 기록을 기본 선택한다.
  const resolvedSelectedTaskRunId =
    selectedTaskRunId !== undefined && taskRunIds.includes(selectedTaskRunId)
      ? selectedTaskRunId
      : taskRunSummaries[0]?.id
  const selectedTaskRun =
    resolvedSelectedTaskRunId === undefined ? undefined : taskRunsById[resolvedSelectedTaskRunId]
  const selectedEvents = useMemo(
    () =>
      resolvedSelectedTaskRunId === undefined
        ? []
        : (eventsByTaskRunId[resolvedSelectedTaskRunId] ?? []),
    [eventsByTaskRunId, resolvedSelectedTaskRunId],
  )
  const selectedVisibleEvents = useMemo(
    () => selectedEvents.filter((event) => !isInternalStepAnchorEvent(event)),
    [selectedEvents],
  )
  const selectedActivities = useMemo(
    () => selectedVisibleEvents.map(toActivityItemView),
    [selectedVisibleEvents],
  )
  const selectedStepRuns = useMemo(
    () =>
      Object.values(stepRunsById)
        .filter((stepRun) => stepRun.task_run_id === resolvedSelectedTaskRunId)
        .filter((stepRun) => !isInternalStepAnchorStepRun(stepRun))
        .sort(compareVisibleStepRuns),
    [resolvedSelectedTaskRunId, stepRunsById],
  )
  const selectedApprovals = useMemo(
    () =>
      Object.values(approvalsById)
        .filter((approval) => approval.task_run_id === resolvedSelectedTaskRunId)
        .sort((first, second) => getTime(first.created_at) - getTime(second.created_at)),
    [approvalsById, resolvedSelectedTaskRunId],
  )
  const selectedPrompt = useMemo(
    () => findPromptForTaskRun(messages, resolvedSelectedTaskRunId),
    [messages, resolvedSelectedTaskRunId],
  )

  useEffect(() => {
    if (selectedTaskRunId === undefined && resolvedSelectedTaskRunId !== undefined) {
      onSelectTaskRun(resolvedSelectedTaskRunId)
    }
  }, [onSelectTaskRun, resolvedSelectedTaskRunId, selectedTaskRunId])

  useEffect(() => {
    if (resolvedSelectedTaskRunId === undefined) return
    if (loadedTaskRunIdsRef.current.has(resolvedSelectedTaskRunId)) return

    const latestEvent = selectedEvents.at(-1)
    const latestStatus = latestEvent?.status ?? latestEvent?.event_type ?? selectedTaskRun?.status

    if (isLiveTaskRunStatus(latestStatus)) {
      return
    }

    loadedTaskRunIdsRef.current.add(resolvedSelectedTaskRunId)
    // snapshot은 현재 TaskRun/StepRun/approval 상태를 채운다.
    // snapshot에 event가 없을 때만 replay로 누락 raw event를 보강한다.
    void (async () => {
      const snapshot = await fetchSnapshot(resolvedSelectedTaskRunId)
      if (!Array.isArray(snapshot?.events) || snapshot.events.length === 0) {
        await replayEvents(resolvedSelectedTaskRunId)
      }
    })().catch(() => undefined)
  }, [
    fetchSnapshot,
    replayEvents,
    resolvedSelectedTaskRunId,
    selectedEvents,
    selectedTaskRun?.status,
  ])

  useEffect(() => {
    taskRunIds.forEach((taskRunId) => {
      if (loadedTaskRunIdsRef.current.has(taskRunId)) return
      const taskRun = taskRunsById[taskRunId]
      const events = eventsByTaskRunId[taskRunId] ?? []
      const latestEvent = events.at(-1)
      const latestStatus = latestEvent?.status ?? latestEvent?.event_type ?? taskRun?.status
      if (isLiveTaskRunStatus(latestStatus)) return
      if (taskRun !== undefined && events.length > 0) return

      loadedTaskRunIdsRef.current.add(taskRunId)
      void (async () => {
        const snapshot = await fetchSnapshot(taskRunId)
        if (!Array.isArray(snapshot?.events) || snapshot.events.length === 0) {
          await replayEvents(taskRunId)
        }
      })().catch(() => undefined)
    })
  }, [eventsByTaskRunId, fetchSnapshot, replayEvents, taskRunIds, taskRunsById])

  useEffect(() => {
    if (resolvedSelectedTaskRunId === undefined) return
    if (selectedTaskRun?.status === undefined || isLiveTaskRunStatus(selectedTaskRun.status)) return
    if (hasMemoryObservation(selectedTaskRun)) return
    if (memoryObservationRefreshIdsRef.current.has(resolvedSelectedTaskRunId)) return

    memoryObservationRefreshIdsRef.current.add(resolvedSelectedTaskRunId)
    const delays = [800, 2500, 5000]
    const timers = delays.map((delay) =>
      window.setTimeout(() => {
        void fetchSnapshot(resolvedSelectedTaskRunId).catch(() => undefined)
      }, delay),
    )

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer))
    }
  }, [fetchSnapshot, resolvedSelectedTaskRunId, selectedTaskRun])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-border border-b p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-muted-foreground truncate text-xs">이 세션의 답변 기록</p>
            <h2 className="text-foreground mt-1 flex items-center gap-2 text-sm font-semibold">
              <span>답변 활동</span>
              {taskRunSummaries.length > 0 && (
                <span className="text-muted-foreground text-xs font-normal">
                  {taskRunSummaries.length}개
                </span>
              )}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="활동 패널 닫기"
            className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="border-border min-h-0 border-b p-3">
        <TaskRunSummaryList
          summaries={taskRunSummaries}
          selectedTaskRunId={resolvedSelectedTaskRunId}
          onSelectTaskRun={onSelectTaskRun}
          onFocusTaskRunMessage={onFocusTaskRunMessage}
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {resolvedSelectedTaskRunId === undefined ? (
          <div className="text-muted-foreground text-sm">선택할 진행 기록이 없습니다.</div>
        ) : (
          <SelectedTaskRunView
            taskRunId={resolvedSelectedTaskRunId}
            taskRun={selectedTaskRun}
            prompt={selectedPrompt}
            steps={selectedStepRuns}
            approvals={selectedApprovals}
            activities={selectedActivities}
            replayNeeded={replayNeededByTaskRunId[resolvedSelectedTaskRunId] === true}
          />
        )}
      </div>
    </div>
  )
}

const hasMemoryObservation = (taskRun?: RawTaskRun) => {
  const resultPayload = taskRun?.result_payload
  return (
    resultPayload !== null &&
    typeof resultPayload === 'object' &&
    !Array.isArray(resultPayload) &&
    'memory_observation' in resultPayload
  )
}

const compareVisibleStepRuns = (first: RawStepRun, second: RawStepRun) => {
  const firstOrder = getVisibleStepOrder(first)
  const secondOrder = getVisibleStepOrder(second)
  if (firstOrder !== undefined && secondOrder !== undefined) {
    return firstOrder - secondOrder
  }
  return (first.sequence ?? 0) - (second.sequence ?? 0)
}

const getVisibleStepOrder = (stepRun: RawStepRun) => {
  if (typeof stepRun.step_order === 'number' && Number.isFinite(stepRun.step_order)) {
    return stepRun.step_order
  }
  if (typeof stepRun.stepOrder === 'number' && Number.isFinite(stepRun.stepOrder)) {
    return stepRun.stepOrder
  }
  return undefined
}

const collectLinkedTaskRunIds = (
  ids: Set<string>,
  eventsByTaskRunId: Record<string, { payload?: unknown }[] | undefined>,
) => {
  let changed = true
  while (changed) {
    changed = false
    ;[...ids].forEach((taskRunId) => {
      const events = eventsByTaskRunId[taskRunId] ?? []
      events.forEach((event) => {
        const linkedTaskRunId = getLinkedTaskRunId(event.payload)
        if (linkedTaskRunId !== undefined && !ids.has(linkedTaskRunId)) {
          ids.add(linkedTaskRunId)
          changed = true
        }
      })
    })
  }
}

const getLinkedTaskRunId = (payload: unknown) => {
  const payloadRecord = toRecord(payload)
  if (payloadRecord === undefined) return undefined
  const result = toRecord(payloadRecord.result) ?? toRecord(payloadRecord.output)
  return stringValue(result?.taskRunId) ?? stringValue(result?.task_run_id)
}

const toRecord = (value: unknown): Record<string, unknown> | undefined => {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }
  return value as Record<string, unknown>
}

const stringValue = (value: unknown) =>
  typeof value === 'string' && value.trim() !== '' ? value.trim() : undefined
