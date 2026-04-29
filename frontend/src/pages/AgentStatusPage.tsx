import { useState, useRef } from 'react'
import { OfficeMap } from '@/components/office/OfficeMap'
import type {
  AgentConfig,
  AgentRuntime,
  Destination,
  SittingState,
} from '@/components/office/types'

// 새 에이전트 추가 시 이 배열에 항목만 추가하면 됩니다.
const AGENT_CONFIGS: AgentConfig[] = [
  {
    id: 'agent01',
    name: 'Agent 01',
    spritePath: '/assets/agents/agent01',
    initialPosition: { x: 1500, y: 667 },
    destinations: {
      desk: { x: 494, y: 405 },
      sofa: { x: 1157, y: 257 },
      floorLean: { x: 1440, y: 260 },
      meeting: { x: 904, y: 95 },
    },
  },
  {
    id: 'agent02',
    name: 'Agent 02',
    spritePath: '/assets/agents/agent02',
    initialPosition: { x: 1560, y: 720 },
    destinations: {
      desk: { x: 630, y: 440 }, // TODO: 실제 2번 책상 좌표로 수정
      sofa: { x: 1200, y: 290 }, // TODO: 실제 좌표로 수정
      floorLean: { x: 1390, y: 300 }, // TODO: 실제 좌표로 수정
      meeting: { x: 950, y: 130 }, // TODO: 실제 좌표로 수정
    },
  },
]

const WALK_SPEED = 100 // px per second on 1600×900 canvas
// 발 올림(0,2) 300ms, 중립(1,3) 120ms
const FRAME_DURATIONS = [300, 120, 300, 120] as const

const DESTINATION_MAP: Record<Destination, { targetState: SittingState; label: string }> = {
  desk: { targetState: 'sitting_desk', label: '책상' },
  sofa: { targetState: 'sitting_sofa', label: '쇼파' },
  floorLean: { targetState: 'sitting_floor_lean', label: '벽' },
  meeting: { targetState: 'sitting_meeting', label: '회의' },
}

const STATE_LABELS: Record<string, string> = {
  idle: '대기 중',
  walking: '이동 중',
  sitting_desk: '작업 중',
  sitting_sofa: '휴식 중',
  sitting_floor_lean: '휴식 중',
  sitting_meeting: '회의 중',
}

function calcDuration(from: { x: number; y: number }, to: { x: number; y: number }): number {
  const dx = to.x - from.x
  const dy = to.y - from.y
  return Math.max(1, Math.sqrt(dx * dx + dy * dy) / WALK_SPEED)
}

function initAgents(): AgentRuntime[] {
  return AGENT_CONFIGS.map((config) => ({
    config,
    position: { ...config.initialPosition },
    state: 'idle' as const,
    targetState: 'sitting_desk' as const,
    walkFrame: 0 as const,
    transitionDuration: 3,
  }))
}

export function AgentStatusPage() {
  const [agents, setAgents] = useState<AgentRuntime[]>(initAgents)
  const walkTimersRef = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({})

  const clearWalkTimer = (agentId: string) => {
    const timer = walkTimersRef.current[agentId]
    if (timer !== undefined) {
      clearTimeout(timer)
      delete walkTimersRef.current[agentId]
    }
  }

  const handleMove = (agentId: string, destination: Destination) => {
    setAgents((prev) => {
      const agent = prev.find((a) => a.config.id === agentId)
      if (!agent || agent.state !== 'idle') return prev

      const destPos = agent.config.destinations[destination]
      const { targetState } = DESTINATION_MAP[destination]
      const duration = calcDuration(agent.position, destPos)

      clearWalkTimer(agentId)

      const scheduleWalkStep = (frame: 0 | 1 | 2 | 3) => {
        walkTimersRef.current[agentId] = setTimeout(() => {
          const next = ((frame + 1) % 4) as 0 | 1 | 2 | 3
          setAgents((p) => p.map((a) => (a.config.id === agentId ? { ...a, walkFrame: next } : a)))
          scheduleWalkStep(next)
        }, FRAME_DURATIONS[frame])
      }
      scheduleWalkStep(0)

      return prev.map((a) =>
        a.config.id === agentId
          ? {
              ...a,
              state: 'walking' as const,
              targetState,
              position: { ...destPos },
              transitionDuration: duration,
            }
          : a,
      )
    })
  }

  const handleAgentArrived = (agentId: string) => {
    clearWalkTimer(agentId)
    setAgents((prev) =>
      prev.map((a) => (a.config.id === agentId ? { ...a, state: a.targetState, walkFrame: 0 } : a)),
    )
  }

  const handleReset = (agentId: string) => {
    clearWalkTimer(agentId)
    setAgents((prev) =>
      prev.map((a) =>
        a.config.id === agentId
          ? {
              ...a,
              position: { ...a.config.initialPosition },
              state: 'idle' as const,
              targetState: 'sitting_desk' as const,
              walkFrame: 0 as const,
            }
          : a,
      ),
    )
  }

  return (
    <div className="relative flex flex-1 overflow-hidden">
      <OfficeMap agents={agents} onAgentArrived={handleAgentArrived} />

      {/* 하단 컨트롤 패널 */}
      <div className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2">
        <div className="flex flex-col gap-2 rounded-2xl border border-white/20 bg-black/60 px-6 py-3 shadow-2xl backdrop-blur-md">
          {agents.map((agent) => (
            <div key={agent.config.id} className="flex items-center gap-4">
              <div className="flex w-36 items-center gap-2">
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    agent.state.startsWith('sitting')
                      ? 'bg-green-400'
                      : agent.state === 'walking'
                        ? 'animate-pulse bg-yellow-400'
                        : 'bg-slate-400'
                  }`}
                />
                <span className="text-sm font-medium text-white">{agent.config.name}</span>
                <span className="text-xs text-white/60">{STATE_LABELS[agent.state]}</span>
              </div>
              <div className="flex gap-2">
                {(Object.keys(DESTINATION_MAP) as Destination[]).map((dest) => (
                  <button
                    key={dest}
                    onClick={() => handleMove(agent.config.id, dest)}
                    disabled={agent.state !== 'idle'}
                    className="rounded-xl bg-white px-4 py-1.5 text-sm font-semibold text-gray-900 shadow-sm transition-opacity hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {DESTINATION_MAP[dest].label}으로
                  </button>
                ))}
                <button
                  onClick={() => handleReset(agent.config.id)}
                  disabled={agent.state === 'idle'}
                  className="rounded-xl border border-white/30 px-4 py-1.5 text-sm font-medium text-white transition-opacity hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  초기화
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
