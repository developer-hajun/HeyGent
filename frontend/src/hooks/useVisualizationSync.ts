import { useEffect, useRef } from 'react'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { UIDestination } from '@/components/office/types'
import type { RawTaskRun } from '@/types/taskRuns'

// 목적지 우선순위 — 같은 에이전트에 여러 task run이 있을 때 더 낮은 값이 우선
// meeting 전환은 handleMove 내부 책상 점유 감지로 처리하므로 여기서는 desk/calling/rest만 반환
const DEST_PRIORITY: Record<UIDestination, number> = {
  desk: 0,
  work: 0,
  calling: 1,
  meeting: 1,
  rest: 2,
}

function resolveDestination(taskRun: RawTaskRun): UIDestination | null {
  const status = taskRun.status?.toUpperCase()

  if (status === 'PENDING') return null
  if (status === 'FAILED') return 'calling'
  if (status === 'COMPLETED' || status === 'CANCELED' || status === 'CANCELLED') return 'rest'
  if (status === 'RUNNING' || status === 'WAITING' || status === 'BLOCKED') return 'desk'

  return null
}

/**
 * useTaskRunStore의 실시간 task run 데이터를 읽어 에이전트 시각화 이동을 트리거한다.
 * displayContext.actorAgent.profileKey 값이 AGENT_CONFIGS의 id와 1:1 매핑된다.
 */
export function useVisualizationSync(handleMove: (agentId: string, dest: UIDestination) => void) {
  const handleMoveRef = useRef(handleMove)
  useEffect(() => {
    handleMoveRef.current = handleMove
  }, [handleMove])

  const taskRunsById = useTaskRunStore((s) => s.taskRunsById)
  const lastDestByAgentId = useRef<Record<string, UIDestination>>({})

  useEffect(() => {
    // 에이전트별로 가장 우선순위 높은 목적지를 결정
    const pendingMoves: Record<string, UIDestination> = {}

    for (const taskRun of Object.values(taskRunsById)) {
      const profileKey = taskRun.displayContext?.actorAgent?.profileKey
      if (!profileKey) continue

      const destination = resolveDestination(taskRun)
      if (destination === null) continue

      const existing = pendingMoves[profileKey]
      if (existing === undefined || DEST_PRIORITY[destination] < DEST_PRIORITY[existing]) {
        pendingMoves[profileKey] = destination
      }
    }

    // 상태가 바뀐 에이전트만 handleMove 호출
    for (const [profileKey, destination] of Object.entries(pendingMoves)) {
      if (lastDestByAgentId.current[profileKey] === destination) continue
      lastDestByAgentId.current[profileKey] = destination
      handleMoveRef.current(profileKey, destination)
    }
  }, [taskRunsById])
}
