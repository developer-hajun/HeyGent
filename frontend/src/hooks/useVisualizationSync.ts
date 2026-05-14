import { useEffect, useRef } from 'react'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { UIDestination } from '@/components/office/types'
import type { RawTaskRun, TaskRunAgentRef } from '@/types/taskRuns'
import type { RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'

// 목적지 우선순위 — 같은 에이전트에 여러 task run이 있을 때 더 낮은 값이 우선
// meeting 전환은 handleMove 내부 책상 점유 감지로 처리하므로 여기서는 desk/calling/rest만 반환
const DEST_PRIORITY: Record<UIDestination, number> = {
  desk: 0,
  work: 0,
  calling: 1,
  meeting: 1,
  rest: 2,
}

// step.started 계열 — 에이전트가 실제로 무언가 시작했음을 나타내는 event_type
const RUNNING_EVENT_TYPES = new Set(['step.started', 'tool.started', 'search.started'])

// actorAgent.profileKey가 없을 때 kind/id로 AGENT_CONFIGS id를 유추한다.
// 백엔드가 팀장 에이전트의 profileKey를 내려주지 않아 kind 기반 매핑이 필요하다.
// profileIdMap: 세션 에이전트 패널의 profileId → spriteId(agentXX) 매핑 — 서브에이전트 연동용
function resolveProfileKey(
  agent?: TaskRunAgentRef | null,
  profileIdMap?: Record<string, string>,
): string | undefined {
  if (!agent) return undefined
  if (agent.kind === 'main') return 'ceo'
  const mappedKey = agent.profileId ?? agent.id
  const fromMap = mappedKey != null ? profileIdMap?.[mappedKey] : undefined
  if (fromMap) return fromMap
  if (agent.profileKey) return agent.profileKey
  if (agent.id) return agent.id
  return undefined
}

// step 단위 종료 event_type — 태스크 전체가 끝난 건 아님 (다음 step이 올 수 있음)
const STEP_TERMINAL_EVENT_TYPES = new Set([
  'step.completed',
  'step.failed',
  'step.canceled',
  'step.cancelled',
])

const TASK_COMPLETED_EVENT_TYPES = new Set(['task.completed', 'session.message.completed'])
const TASK_FAILED_EVENT_TYPES = new Set(['task.failed', 'session.message.failed'])
const TASK_CANCELED_EVENT_TYPES = new Set(['task.canceled', 'task.cancelled'])

function getTimestamp(value: unknown): number {
  if (typeof value !== 'string') return 0
  const time = new Date(value).getTime()
  return Number.isFinite(time) ? time : 0
}

function getTaskRunSortTime(taskRun: RawTaskRun, latestEvent?: RawTaskEventPayload): number {
  return Math.max(
    getTimestamp(latestEvent?.occurred_at),
    getTimestamp(taskRun.updated_at),
    getTimestamp(taskRun.completed_at),
    getTimestamp(taskRun.created_at),
  )
}

/**
 * task run 상태를 결정한다.
 * 최신 이벤트(task.event)의 status가 있으면 우선 사용 — taskRunsById보다 실시간.
 * status가 없으면 event_type으로 보조 판단하되, step 단위 종료는 무시 (태스크가 아직 진행 중일 수 있음).
 */
function resolveDestination(
  taskRun: RawTaskRun,
  latestEvent?: RawTaskEventPayload,
): UIDestination | null {
  if (latestEvent !== undefined) {
    if (TASK_COMPLETED_EVENT_TYPES.has(latestEvent.event_type)) return 'rest'
    if (TASK_FAILED_EVENT_TYPES.has(latestEvent.event_type)) return 'calling'
    if (TASK_CANCELED_EVENT_TYPES.has(latestEvent.event_type)) return 'rest'
  }

  // step 단위 종료 이벤트(step.completed 등)의 status는 task 완료를 의미하지 않음
  // — step event가 아닌 경우에만 event status를 task 상태 판단에 사용
  const eventStatus =
    latestEvent != null && !STEP_TERMINAL_EVENT_TYPES.has(latestEvent.event_type)
      ? latestEvent.status
      : undefined
  const status = (eventStatus ?? taskRun.status)?.toUpperCase()

  if (!status || status === 'PENDING') return null
  if (status === 'FAILED') return 'calling'
  if (status === 'COMPLETED' || status === 'CANCELED' || status === 'CANCELLED') return 'rest'
  if (status === 'RUNNING' || status === 'WAITING' || status === 'BLOCKED') return 'desk'

  // status 필드 없을 때 event_type으로 보조 판단
  if (latestEvent && !STEP_TERMINAL_EVENT_TYPES.has(latestEvent.event_type)) {
    if (RUNNING_EVENT_TYPES.has(latestEvent.event_type)) return 'desk'
    if (latestEvent.event_type === 'step.waiting') return 'desk'
  }

  return null
}

/**
 * useTaskRunStore의 실시간 task run / task.event 데이터를 읽어 에이전트 시각화 이동을 트리거한다.
 * - Spec 4 (taskRuns.active.list): taskRunsById 초기 상태
 * - Spec 1 (task.event): eventsByTaskRunId 실시간 갱신 → 최신 이벤트 status/event_type 반영
 * - profileIdMap: 세션 에이전트 profileId → spriteId(agentXX) 매핑 — 서브에이전트 task run 연동용
 */
export function useVisualizationSync(
  handleMove: (agentId: string, dest: UIDestination) => void,
  sessionId?: string,
  profileIdMap?: Record<string, string>,
) {
  const handleMoveRef = useRef(handleMove)
  useEffect(() => {
    handleMoveRef.current = handleMove
  }, [handleMove])

  const taskRunsById = useTaskRunStore((s) => s.taskRunsById)
  const eventsByTaskRunId = useTaskRunStore((s) => s.eventsByTaskRunId)
  const lastDestByAgentId = useRef<Record<string, UIDestination>>({})

  useEffect(() => {
    const pendingMoves: Record<string, { destination: UIDestination; sortTime: number }> = {}

    for (const taskRun of Object.values(taskRunsById)) {
      if (
        sessionId !== undefined &&
        taskRun.session_id !== undefined &&
        taskRun.session_id !== sessionId
      ) {
        continue
      }

      const profileKey = resolveProfileKey(taskRun.displayContext?.actorAgent, profileIdMap)
      if (!profileKey) continue

      // 해당 task run의 최신 이벤트 (sequence 순 정렬된 배열의 마지막)
      const events = eventsByTaskRunId[taskRun.task_run_id] ?? []
      const latestEvent = events.length > 0 ? events[events.length - 1] : undefined

      const destination = resolveDestination(taskRun, latestEvent)
      if (destination === null) continue

      const sortTime = getTaskRunSortTime(taskRun, latestEvent)
      const existing = pendingMoves[profileKey]
      if (
        existing === undefined ||
        sortTime > existing.sortTime ||
        (sortTime === existing.sortTime &&
          DEST_PRIORITY[destination] < DEST_PRIORITY[existing.destination])
      ) {
        pendingMoves[profileKey] = { destination, sortTime }
      }
    }

    for (const [profileKey, { destination }] of Object.entries(pendingMoves)) {
      if (lastDestByAgentId.current[profileKey] === destination) continue
      lastDestByAgentId.current[profileKey] = destination
      handleMoveRef.current(profileKey, destination)
    }
  }, [taskRunsById, eventsByTaskRunId, sessionId, profileIdMap])
}
