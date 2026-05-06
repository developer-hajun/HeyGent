import { useState } from 'react'
import { useNavigate } from 'react-router'
import { FloorAgentSprite } from '@/components/office/FloorAgentSprite'

const FLOORS = [
  {
    sessionId: '3',
    label: '3F',
    top: '13%',
    left: '15%',
    width: '72%',
    height: '26%',
    agentSize: 72, // ← 에이전트 크기 (px)
    agentBottom: -1, // ← 층 바닥 기준 위치 (%)
    agentMinX: 40, // ← 에이전트 왼쪽 이동 한계 (%)
    agentMaxX: 85, // ← 에이전트 오른쪽 이동 한계 (%)
    agents: [
      { agentId: 'agent01', initialXPct: 30 },
      { agentId: 'agent02', initialXPct: 55 },
      { agentId: 'agent03', initialXPct: 80 },
    ],
  },
  {
    sessionId: '2',
    label: '2F',
    top: '38%',
    left: '15%',
    width: '72%',
    height: '26%',
    agentSize: 71, // ← 에이전트 크기 (px)
    agentBottom: 5, // ← 층 바닥 기준 위치 (%)
    agentMinX: 30, // ← 에이전트 왼쪽 이동 한계 (%)
    agentMaxX: 85, // ← 에이전트 오른쪽 이동 한계 (%)
    agents: [
      { agentId: 'agent04', initialXPct: 30 },
      { agentId: 'agent05', initialXPct: 55 },
      { agentId: 'agent06', initialXPct: 78 },
    ],
  },
  {
    sessionId: '1',
    label: '1F',
    top: '63%',
    left: '15%',
    width: '68%',
    height: '25%',
    agentSize: 70, // ← 에이전트 크기 (px)
    agentBottom: 8, // ← 층 바닥 기준 위치 (%)
    agentMinX: 25, // ← 에이전트 왼쪽 이동 한계 (%)
    agentMaxX: 85, // ← 에이전트 오른쪽 이동 한계 (%)
    agents: [
      { agentId: 'agent07', initialXPct: 25 },
      { agentId: 'agent08', initialXPct: 42 },
      { agentId: 'agent09', initialXPct: 62 },
      { agentId: 'agent10', initialXPct: 80 },
    ],
  },
]

export function BuildingOverviewPage() {
  const navigate = useNavigate()
  const [hoveredFloor, setHoveredFloor] = useState<string | null>(null)

  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-[#7e7a8e]">
      <div
        className="relative inline-block"
        style={{
          maskImage:
            'linear-gradient(to right, transparent 0%, black 10%, black 95%, transparent 100%), linear-gradient(to bottom, transparent 0%, black 6%, black 96%, transparent 100%)',
          maskComposite: 'intersect',
          WebkitMaskImage:
            'linear-gradient(to right, transparent 0%, black 10%, black 95%, transparent 100%), linear-gradient(to bottom, transparent 0%, black 6%, black 96%, transparent 100%)',
          WebkitMaskComposite: 'source-in',
        }}
      >
        <img
          src="/assets/maps/building_overview.png"
          alt="Building Overview"
          draggable={false}
          className="block select-none"
          style={{ maxHeight: 'calc(100vh - 120px)', maxWidth: '100%' }}
        />
        {FLOORS.map((floor) => (
          <div
            key={floor.sessionId}
            style={{
              position: 'absolute',
              top: floor.top,
              left: floor.left,
              width: floor.width,
              height: floor.height,
              overflow: 'hidden',
            }}
          >
            {floor.agents.map((agent) => (
              <FloorAgentSprite
                key={agent.agentId}
                agentId={agent.agentId}
                initialXPct={agent.initialXPct}
                size={floor.agentSize}
                bottomPct={floor.agentBottom}
                minXPct={floor.agentMinX}
                maxXPct={floor.agentMaxX}
              />
            ))}

            <div
              className="absolute inset-0 cursor-pointer rounded transition-all duration-200"
              onClick={() => navigate(`/agent-status/${floor.sessionId}`)}
              onMouseEnter={() => setHoveredFloor(floor.sessionId)}
              onMouseLeave={() => setHoveredFloor(null)}
              style={{
                background:
                  hoveredFloor === floor.sessionId ? 'rgba(255,255,255,0.1)' : 'transparent',
                boxShadow:
                  hoveredFloor === floor.sessionId
                    ? 'inset 0 0 0 2px rgba(255,255,255,0.3)'
                    : 'none',
              }}
            />

            {hoveredFloor === floor.sessionId && (
              <div className="absolute top-2 right-2 z-10 rounded-lg bg-black/60 px-3 py-1 backdrop-blur-sm">
                <span className="text-sm font-bold text-white">{floor.label} 세션 열기</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
