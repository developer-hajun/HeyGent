import { useState, useRef } from 'react'
import { OfficeMap } from '@/components/office/OfficeMap'
import type {
  AgentConfig,
  AgentRuntime,
  Destination,
  SittingState,
} from '@/components/office/types'

// 버튼으로 조작 가능한 에이전트 (API 연결 전 임시)
const CONTROLLABLE_AGENTS = new Set(['agent01', 'agent02', 'agent05'])

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
      calling: { x: 1111, y: 658 },
    },
  },
  {
    id: 'agent02',
    name: 'Agent 02',
    spritePath: '/assets/agents/agent02',
    initialPosition: { x: 1560, y: 720 },
    destinations: {
      desk: { x: 630, y: 440 },
      sofa: { x: 1200, y: 290 },
      floorLean: { x: 1390, y: 300 },
      meeting: { x: 950, y: 130 },
      calling: { x: 1111, y: 658 },
    },
  },
  {
    id: 'agent03',
    name: 'Agent 03',
    spritePath: '/assets/agents/agent03',
    initialPosition: { x: 1450, y: 720 },
    destinations: {
      desk: { x: 494, y: 450 },
      sofa: { x: 1110, y: 290 },
      floorLean: { x: 1390, y: 260 },
      meeting: { x: 860, y: 130 },
      calling: { x: 1111, y: 658 },
    },
  },
  {
    id: 'agent04',
    name: 'Agent 04',
    spritePath: '/assets/agents/agent04',
    initialPosition: { x: 1500, y: 770 },
    destinations: {
      desk: { x: 550, y: 405 },
      sofa: { x: 1157, y: 310 },
      floorLean: { x: 1440, y: 310 },
      meeting: { x: 950, y: 95 },
      calling: { x: 1111, y: 658 },
    },
  },
  {
    id: 'agent05',
    name: 'Agent 05',
    spritePath: '/assets/agents/agent05',
    initialPosition: { x: 1560, y: 770 },
    destinations: {
      desk: { x: 550, y: 450 },
      sofa: { x: 1110, y: 310 },
      floorLean: { x: 1340, y: 300 },
      meeting: { x: 860, y: 95 },
      calling: { x: 1111, y: 658 },
    },
  },
]

const WALK_SPEED = 100
const FRAME_DURATIONS = [300, 120, 300, 120] as const

const DESTINATION_MAP: Record<Destination, { targetState: SittingState; label: string }> = {
  desk: { targetState: 'sitting_desk', label: '책상' },
  sofa: { targetState: 'sitting_sofa', label: '쇼파' },
  floorLean: { targetState: 'sitting_floor_lean', label: '벽' },
  meeting: { targetState: 'sitting_meeting', label: '회의' },
  calling: { targetState: 'sitting_calling', label: '전화' },
}

const STATE_LABELS: Record<string, string> = {
  idle: '대기 중',
  walking: '이동 중',
  sitting_desk: '작업 중',
  sitting_sofa: '휴식 중',
  sitting_floor_lean: '휴식 중',
  sitting_meeting: '회의 중',
  sitting_calling: '통화 중',
}

function stateColor(state: string) {
  if (state === 'sitting_calling') return 'bg-blue-400'
  if (state.startsWith('sitting')) return 'bg-green-400'
  if (state === 'walking') return 'bg-yellow-400'
  return 'bg-slate-500'
}

function calcDuration(from: { x: number; y: number }, to: { x: number; y: number }): number {
  const dx = to.x - from.x
  const dy = to.y - from.y
  return Math.max(1, Math.sqrt(dx * dx + dy * dy) / WALK_SPEED)
}

function initAgents(): AgentRuntime[] {
  return AGENT_CONFIGS.map((config) => {
    const isFixed = !CONTROLLABLE_AGENTS.has(config.id)
    return {
      config,
      position: isFixed ? { ...config.destinations.floorLean } : { ...config.initialPosition },
      state: isFixed ? ('sitting_floor_lean' as const) : ('idle' as const),
      targetState: 'sitting_desk' as const,
      walkFrame: 0 as const,
      transitionDuration: 3,
    }
  })
}

export function AgentStatusPage() {
  const [agents, setAgents] = useState<AgentRuntime[]>(initAgents)
  const [selectedId, setSelectedId] = useState<string>('agent01')
  const [ceoMode, setCeoMode] = useState<'desk' | 'explain' | null>(null)
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

  const selectedAgent = agents.find((a) => a.config.id === selectedId)

  return (
    <div className="relative flex flex-1 overflow-hidden">
      <OfficeMap agents={agents} onAgentArrived={handleAgentArrived} ceoMode={ceoMode} />

      <div className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2">
        <div className="flex flex-col gap-2.5 rounded-2xl border border-white/20 bg-black/60 px-5 py-3 shadow-2xl backdrop-blur-md">
          {/* 에이전트 탭 */}
          <div className="flex items-center gap-1.5">
            {agents.map((agent) => (
              <button
                key={agent.config.id}
                onClick={() => setSelectedId(agent.config.id)}
                className={`relative rounded-lg px-3 py-1 text-xs font-bold transition-colors ${
                  selectedId === agent.config.id
                    ? 'bg-white text-gray-900'
                    : 'bg-white/10 text-white/60 hover:bg-white/20 hover:text-white'
                }`}
              >
                {agent.config.id.replace('agent', '')}
                <span
                  className={`absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full border border-black/50 ${stateColor(agent.state)} ${agent.state === 'walking' ? 'animate-pulse' : ''}`}
                />
              </button>
            ))}
            <div className="mx-0.5 h-4 w-px bg-white/20" />
            {(['desk', 'explain'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setCeoMode((prev) => (prev === mode ? null : mode))}
                className={`rounded-lg px-3 py-1 text-xs font-bold transition-colors ${
                  ceoMode === mode
                    ? 'bg-amber-400 text-gray-900'
                    : 'bg-white/10 text-white/40 hover:bg-white/20 hover:text-white'
                }`}
              >
                {mode === 'desk' ? 'CEO 책상' : 'CEO 화이트보드'}
              </button>
            ))}
          </div>

          {/* 선택된 에이전트 컨트롤 */}
          {selectedAgent && (
            <div className="flex items-center gap-3">
              <div className="flex w-28 flex-col">
                <span className="text-sm font-medium text-white">{selectedAgent.config.name}</span>
                <span className="text-xs text-white/50">{STATE_LABELS[selectedAgent.state]}</span>
              </div>
              {CONTROLLABLE_AGENTS.has(selectedAgent.config.id) && (
                <div className="flex gap-1.5">
                  {(Object.keys(DESTINATION_MAP) as Destination[]).map((dest) => (
                    <button
                      key={dest}
                      onClick={() => handleMove(selectedAgent.config.id, dest)}
                      disabled={selectedAgent.state !== 'idle'}
                      className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-gray-900 shadow-sm transition-opacity hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {DESTINATION_MAP[dest].label}으로
                    </button>
                  ))}
                  <button
                    onClick={() => handleReset(selectedAgent.config.id)}
                    disabled={selectedAgent.state === 'idle'}
                    className="rounded-lg border border-white/30 px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    초기화
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
