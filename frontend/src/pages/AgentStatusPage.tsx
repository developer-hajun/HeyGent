import { useState, useRef } from 'react'
import { OfficeMap } from '@/components/office/OfficeMap'
import type { AgentConfig, AgentRuntime } from '@/components/office/types'

const AGENT_CONFIGS: AgentConfig[] = [
  {
    id: 'agent01',
    name: 'Agent 01',
    spritePath: '/assets/agents/agent01',
    initialPosition: { x: 1500, y: 667 },
    deskPosition: { x: 494, y: 405 },
  },
]

const WALK_SPEED = 100 // px per second on 1600×900 canvas

function calcDuration(from: { x: number; y: number }, to: { x: number; y: number }): number {
  const dx = to.x - from.x
  const dy = to.y - from.y
  return Math.max(1, Math.sqrt(dx * dx + dy * dy) / WALK_SPEED)
}

function initAgents(): AgentRuntime[] {
  return AGENT_CONFIGS.map((config) => ({
    config,
    position: { ...config.initialPosition },
    state: 'idle',
    walkFrame: 0,
    transitionDuration: 3,
  }))
}

const STATE_LABELS: Record<string, string> = {
  idle: '대기 중',
  walking: '이동 중',
  sitting: '작업 중',
}

export function AgentStatusPage() {
  const [agents, setAgents] = useState<AgentRuntime[]>(initAgents)
  const walkIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleMove = (agentId: string) => {
    setAgents((prev) => {
      const agent = prev.find((a) => a.config.id === agentId)
      if (!agent || agent.state !== 'idle') return prev

      const duration = calcDuration(agent.position, agent.config.deskPosition)

      if (walkIntervalRef.current) clearInterval(walkIntervalRef.current)
      walkIntervalRef.current = setInterval(() => {
        setAgents((p) =>
          p.map((a) =>
            a.config.id === agentId ? { ...a, walkFrame: ((a.walkFrame + 1) % 2) as 0 | 1 } : a,
          ),
        )
      }, 300)

      return prev.map((a) =>
        a.config.id === agentId
          ? {
              ...a,
              state: 'walking' as const,
              position: { ...a.config.deskPosition },
              transitionDuration: duration,
            }
          : a,
      )
    })
  }

  const handleAgentArrived = (agentId: string) => {
    if (walkIntervalRef.current) {
      clearInterval(walkIntervalRef.current)
      walkIntervalRef.current = null
    }
    setAgents((prev) =>
      prev.map((a) => (a.config.id === agentId ? { ...a, state: 'sitting', walkFrame: 0 } : a)),
    )
  }

  const handleReset = () => {
    if (walkIntervalRef.current) {
      clearInterval(walkIntervalRef.current)
      walkIntervalRef.current = null
    }
    setAgents(initAgents())
  }

  const agent = agents[0]

  return (
    <div className="relative flex flex-1 overflow-hidden">
      <OfficeMap agents={agents} onAgentArrived={handleAgentArrived} />

      {/* 하단 컨트롤 패널 */}
      <div className="absolute bottom-6 left-1/2 z-20 -translate-x-1/2">
        <div className="flex items-center gap-4 rounded-2xl border border-white/20 bg-black/60 px-6 py-3 shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                agent.state === 'sitting'
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
            <button
              onClick={() => handleMove('agent01')}
              disabled={agent.state !== 'idle'}
              className="rounded-xl bg-white px-4 py-1.5 text-sm font-semibold text-gray-900 shadow-sm transition-opacity hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              출근 시작
            </button>
            <button
              onClick={handleReset}
              disabled={agent.state === 'idle'}
              className="rounded-xl border border-white/30 px-4 py-1.5 text-sm font-medium text-white transition-opacity hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            >
              초기화
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
