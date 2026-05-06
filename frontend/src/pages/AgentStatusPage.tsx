import { useState, useRef } from 'react'
import { OfficeMap } from '@/components/office/OfficeMap'
import type {
  AgentConfig,
  AgentRuntime,
  Destination,
  SittingState,
} from '@/components/office/types'

// 버튼으로 조작 가능한 에이전트 (API 연결 전 임시)
const CONTROLLABLE_AGENTS = new Set(['agent01', 'agent02', 'agent05', 'agent06', 'agent09'])

// 에이전트별 고정 목적지 (API 연결 전 임시)
const AGENT_FIXED_DEST: Record<string, Destination> = {
  agent01: 'desk',
  agent02: 'meeting',
  agent03: 'floorLean',
  agent04: 'sofa',
  agent05: 'calling',
  agent06: 'sofa',
  agent07: 'meeting',
  agent08: 'desk',
  agent09: 'calling',
  agent10: 'sofa',
}

// 새 에이전트 추가 시 이 배열에 항목만 추가하면 됩니다.
const AGENT_CONFIGS: AgentConfig[] = [
  {
    id: 'agent01',
    name: 'Agent 01',
    spritePath: '/assets/agents/agent01',
    stateScales: { sitting_meeting: 0.85, sitting_calling: 0.85, sitting_floor_lean: 0.85 },
    initialPosition: { x: 1500, y: 667 },
    destinations: {
      desk: { x: 470, y: 395 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1545, y: 285 },
      meeting: { x: 415, y: 130 },
      calling: { x: 1110, y: 660 },
    },
  },
  {
    id: 'agent02',
    name: 'Agent 02',
    spritePath: '/assets/agents/agent02',
    stateScales: { sitting_meeting: 0.85, sitting_floor_lean: 0.85, sitting_calling: 0.85 },
    initialPosition: { x: 1560, y: 720 },
    destinations: {
      desk: { x: 650, y: 458 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1070, y: 285 },
      meeting: { x: 925, y: 90 },
      calling: { x: 840, y: 350 },
    },
  },
  {
    id: 'agent03',
    name: 'Agent 03',
    spritePath: '/assets/agents/agent03',
    scale: 0.85,
    initialPosition: { x: 1450, y: 720 },
    destinations: {
      desk: { x: 470, y: 395 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1215, y: 370 },
      meeting: { x: 715, y: 215 },
      calling: { x: 990, y: 750 },
    },
  },
  {
    id: 'agent04',
    name: 'Agent 04',
    spritePath: '/assets/agents/agent04',
    scale: 0.87,
    stateScales: { sitting_desk: 1.1, sitting_floor_lean: 0.85 },
    initialPosition: { x: 1500, y: 770 },
    destinations: {
      desk: { x: 465, y: 595 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1415, y: 360 },
      meeting: { x: 920, y: 220 },
      calling: { x: 1110, y: 655 },
    },
  },
  {
    id: 'agent05',
    name: 'Agent 05',
    spritePath: '/assets/agents/agent05',
    stateScales: {
      sitting_desk: 0.92,
      sitting_meeting: 0.85,
      sitting_floor_lean: 0.8,
      sitting_calling: 0.9,
    },
    initialPosition: { x: 1560, y: 770 },
    destinations: {
      desk: { x: 825, y: 520 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1535, y: 425 },
      meeting: { x: 415, y: 130 },
      calling: { x: 1334, y: 665 },
    },
  },
  {
    id: 'agent06',
    name: 'Agent 06',
    spritePath: '/assets/agents/agent06',
    stateScales: {
      sitting_floor_lean: 0.85,
      sitting_meeting: 0.85,
      sitting_calling: 0.85,
      sitting_sofa: 0.85,
    },
    initialPosition: { x: 1380, y: 667 },
    destinations: {
      desk: { x: 825, y: 520 },
      sofa: { x: 1140, y: 230 },
      floorLean: { x: 1290, y: 260 },
      meeting: { x: 925, y: 90 },
      calling: { x: 1070, y: 658 },
    },
  },
  {
    id: 'agent07',
    name: 'Agent 07',
    spritePath: '/assets/agents/agent07',
    stateScales: {
      sitting_meeting: 0.8,
      sitting_sofa: 0.85,
      sitting_floor_lean: 0.85,
      sitting_calling: 0.85,
    },
    initialPosition: { x: 140, y: 750 },
    destinations: {
      desk: { x: 465, y: 595 },
      sofa: { x: 1140, y: 230 },
      floorLean: { x: 1340, y: 280 },
      meeting: { x: 850, y: 65 },
      calling: { x: 1430, y: 840 },
    },
  },
  {
    id: 'agent08',
    name: 'Agent 08',
    spritePath: '/assets/agents/agent08',
    scale: 0.85,
    stateScales: { sitting_sofa: 1.1, sitting_desk: 0.95, sitting_calling: 1.1 },
    initialPosition: { x: 80, y: 820 },
    destinations: {
      desk: { x: 650, y: 458 },
      sofa: { x: 1140, y: 230 },
      floorLean: { x: 995, y: 340 },
      meeting: { x: 670, y: 105 },
      calling: { x: 240, y: 710 },
    },
  },
  {
    id: 'agent09',
    name: 'Agent 09',
    spritePath: '/assets/agents/agent09',
    scale: 0.85,
    stateScales: { sitting_desk: 1.1 },
    initialPosition: { x: 1380, y: 770 },
    destinations: {
      desk: { x: 650, y: 685 },
      sofa: { x: 1140, y: 230 },
      floorLean: { x: 1380, y: 490 },
      meeting: { x: 785, y: 245 },
      calling: { x: 1200, y: 658 },
    },
  },
  {
    id: 'agent10',
    name: 'Agent 10',
    spritePath: '/assets/agents/agent10',
    scale: 0.85,
    initialPosition: { x: 200, y: 820 },
    destinations: {
      desk: { x: 650, y: 685 },
      sofa: { x: 1140, y: 230 },
      floorLean: { x: 1310, y: 460 },
      meeting: { x: 920, y: 220 },
      calling: { x: 1250, y: 660 },
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
  return AGENT_CONFIGS.map((config) => ({
    config,
    position: { ...config.initialPosition },
    state: 'idle' as const,
    targetState: 'sitting_desk' as const,
    walkFrame: 0 as const,
    transitionDuration: 3,
  }))
}

const DESTINATIONS: Destination[] = ['desk', 'sofa', 'floorLean', 'meeting', 'calling']

export function AgentStatusPage() {
  const [agents, setAgents] = useState<AgentRuntime[]>(initAgents)
  const [selectedId, setSelectedId] = useState<string>(
    () => localStorage.getItem('debug_selectedId') ?? 'agent01',
  )
  const [ceoMode, setCeoMode] = useState<'desk' | 'explain'>('desk')
  const [debugDestMap, setDebugDestMap] = useState<Record<string, Destination>>(() =>
    JSON.parse(localStorage.getItem('debug_destMap') ?? '{}'),
  )
  const [panelTop, setPanelTop] = useState(false)
  const walkTimersRef = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({})

  const setSelectedIdPersist = (id: string) => {
    localStorage.setItem('debug_selectedId', id)
    setSelectedId(id)
  }

  const setDebugDestPersist = (agentId: string, dest: Destination | null) => {
    setDebugDestMap((prev) => {
      const next = { ...prev }
      if (dest === null) delete next[agentId]
      else next[agentId] = dest
      localStorage.setItem('debug_destMap', JSON.stringify(next))
      return next
    })
  }

  const displayAgents = agents.map((a) => {
    const dest = debugDestMap[a.config.id]
    if (!dest) return a
    return {
      ...a,
      position: a.config.destinations[dest],
      state: DESTINATION_MAP[dest].targetState,
      transitionDuration: 0,
    }
  })

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
      <OfficeMap agents={displayAgents} onAgentArrived={handleAgentArrived} ceoMode={ceoMode} />

      {/* 좌표 디버그 패널 */}
      <div className="absolute top-4 right-4 z-20">
        <div className="flex flex-col gap-2 rounded-2xl border border-white/20 bg-black/60 px-4 py-3 shadow-2xl backdrop-blur-md">
          <span className="text-xs font-bold text-white/50">목적지 미리보기</span>
          <div className="flex gap-1.5">
            {DESTINATIONS.map((dest) => (
              <button
                key={dest}
                onClick={() =>
                  setDebugDestPersist(selectedId, debugDestMap[selectedId] === dest ? null : dest)
                }
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                  debugDestMap[selectedId] === dest
                    ? 'bg-yellow-400 text-gray-900'
                    : 'bg-white/10 text-white/60 hover:bg-white/20 hover:text-white'
                }`}
              >
                {DESTINATION_MAP[dest].label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className={`absolute left-1/2 z-20 -translate-x-1/2 ${panelTop ? 'top-4' : 'bottom-6'}`}>
        <div className="flex flex-col gap-2.5 rounded-2xl border border-white/20 bg-black/60 px-5 py-3 shadow-2xl backdrop-blur-md">
          {/* 에이전트 탭 */}
          <div className="flex items-center gap-1.5">
            {agents.map((agent) => (
              <button
                key={agent.config.id}
                onClick={() => setSelectedIdPersist(agent.config.id)}
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
            <button
              onClick={() => setPanelTop((prev) => !prev)}
              className="rounded-lg bg-white/10 px-2 py-1 text-xs text-white/60 transition-colors hover:bg-white/20 hover:text-white"
              title="패널 위치 이동"
            >
              {panelTop ? '▼' : '▲'}
            </button>
            <div className="mx-0.5 h-4 w-px bg-white/20" />
            <button
              onClick={() => setCeoMode((prev) => (prev === 'desk' ? 'explain' : 'desk'))}
              className="rounded-lg bg-amber-400 px-3 py-1 text-xs font-bold text-gray-900 transition-colors hover:bg-amber-300"
            >
              {ceoMode === 'desk' ? 'CEO 책상' : 'CEO 화이트보드'}
            </button>
          </div>

          {/* 선택된 에이전트 컨트롤 */}
          {selectedAgent && (
            <div className="flex items-center gap-3">
              <div className="flex w-28 flex-col">
                <span className="text-sm font-medium text-white">{selectedAgent.config.name}</span>
                <span className="text-xs text-white/50">{STATE_LABELS[selectedAgent.state]}</span>
              </div>
              {CONTROLLABLE_AGENTS.has(selectedAgent.config.id) &&
                (() => {
                  const dest = AGENT_FIXED_DEST[selectedAgent.config.id]
                  return (
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => handleMove(selectedAgent.config.id, dest)}
                        disabled={selectedAgent.state !== 'idle'}
                        className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-gray-900 shadow-sm transition-opacity hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {DESTINATION_MAP[dest].label}
                      </button>
                      <button
                        onClick={() => handleReset(selectedAgent.config.id)}
                        disabled={selectedAgent.state === 'idle'}
                        className="rounded-lg border border-white/30 px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        초기화
                      </button>
                    </div>
                  )
                })()}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
