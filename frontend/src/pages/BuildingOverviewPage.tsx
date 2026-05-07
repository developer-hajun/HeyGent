import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router'
import { FloorAgentSprite } from '@/components/office/FloorAgentSprite'

const IMG_W = 1586
const IMG_H = 992

function getBuildingBgSrc(): string {
  const hour = new Date().getHours()
  if (hour >= 8 && hour < 16) return '/assets/maps/building_bg_day.png'
  if (hour >= 6 && hour < 8) return '/assets/maps/building_bg_sunset.png'
  if (hour >= 16 && hour < 18) return '/assets/maps/building_bg_sunset.png'
  if (hour >= 18 && hour < 20) return '/assets/maps/building_bg_dusk.png'
  return '/assets/maps/building_bg_night.png'
}

const FLOORS = [
  {
    sessionId: '3',
    label: '3F',
    top: '13%',
    left: '15%',
    width: '72%',
    height: '26%',
    agentSize: 90,
    agentBottom: 4,
    agentMinX: 40,
    agentMaxX: 85,
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
    agentSize: 90,
    agentBottom: 10,
    agentMinX: 30,
    agentMaxX: 85,
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
    agentSize: 90,
    agentBottom: 19,
    agentMinX: 25,
    agentMaxX: 85,
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
  const [bgSrc, setBgSrc] = useState(getBuildingBgSrc)
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    function scheduleNext() {
      const now = new Date()
      const boundaries = [6, 8, 16, 18, 20]
      const totalMinutes = now.getHours() * 60 + now.getMinutes()
      const nextBoundaryMinutes =
        boundaries.map((h) => h * 60).find((m) => m > totalMinutes) ?? 6 * 60 + 24 * 60
      const msUntilNext = (nextBoundaryMinutes - totalMinutes) * 60_000 - now.getSeconds() * 1000

      return setTimeout(() => {
        setBgSrc(getBuildingBgSrc())
        scheduleNext()
      }, msUntilNext)
    }

    const timer = scheduleNext()
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setScale(Math.min(width / IMG_W, height / IMG_H))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="relative flex-1 overflow-hidden">
      {/* 배경: 시간대별 이미지로 화면 전체 채움 */}
      <img
        src={bgSrc}
        alt=""
        draggable={false}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
        }}
      />

      {/* 전경: building_overview.png + 층별 클릭 영역 */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: IMG_W,
          height: IMG_H,
          transform: `translate(-50%, -50%) scale(${scale})`,
          transformOrigin: 'center center',
        }}
      >
        <img
          src="/assets/maps/building_overview.png"
          alt="Building Overview"
          draggable={false}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            display: 'block',
          }}
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
