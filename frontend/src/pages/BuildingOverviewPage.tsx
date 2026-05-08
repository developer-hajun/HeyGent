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
    // agent container bounds
    top: '13.5%',
    left: '20%',
    width: '61%',
    height: '24%',
    // SVG polygon matching the actual glass panel (within 1586×992 canvas)
    svgPoints: '326,178 1252,142 1290,157 1290,363 1252,354 326,375',
    labelTop: 165,
    labelRight: 304,
    agentSize: 85,
    agentBottom: 0,
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
    top: '40%',
    left: '20%',
    width: '61%',
    height: '21%',
    svgPoints: '326,407 1252,395 1290,403 1290,593 1252,598 326,595',
    labelTop: 411,
    labelRight: 304,
    agentSize: 85,
    agentBottom: 0,
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
    left: '20%',
    width: '59%',
    height: '21%',
    svgPoints: '326,627 1251,638 1251,834 326,810',
    labelTop: 646,
    labelRight: 343,
    agentSize: 85,
    agentBottom: 5,
    agentMinX: 25,
    agentMaxX: 82,
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
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null)

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const canvasX = Math.round(IMG_W / 2 + (mx - rect.width / 2) / scale)
    const canvasY = Math.round(IMG_H / 2 + (my - rect.height / 2) / scale)
    setMousePos({ x: canvasX, y: canvasY })
  }

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
    <div
      ref={containerRef}
      className="relative flex-1 overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setMousePos(null)}
    >
      {mousePos && (
        <div
          style={{ position: 'fixed', top: 8, left: 8, zIndex: 9999 }}
          className="pointer-events-none rounded bg-black/80 px-2 py-1 font-mono text-xs text-white"
        >
          x: {mousePos.x}, y: {mousePos.y}
        </div>
      )}
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

        {/* 회사 로고 오버레이 */}
        <img
          src="/assets/maps/logo.png"
          alt="Logo"
          draggable={false}
          style={{
            position: 'absolute',
            top: 48,
            left: 1070,
            width: 180,
            height: 'auto',
            pointerEvents: 'none',
          }}
        />
        {/* 에이전트 스프라이트 컨테이너 (클릭 이벤트는 SVG에서 처리) */}
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
              pointerEvents: 'none',
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
          </div>
        ))}

        {/* SVG 오버레이: 실제 유리 패널 모양에 맞는 정확한 hover/click 영역 */}
        <svg
          viewBox={`0 0 ${IMG_W} ${IMG_H}`}
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
        >
          {FLOORS.map((floor) => (
            <polygon
              key={floor.sessionId}
              points={floor.svgPoints}
              fill={hoveredFloor === floor.sessionId ? 'rgba(255,255,255,0.22)' : 'transparent'}
              stroke={hoveredFloor === floor.sessionId ? 'rgba(255,255,255,0.7)' : 'transparent'}
              strokeWidth="2"
              style={{ cursor: 'pointer' }}
              onClick={() => navigate(`/agent-status/${floor.sessionId}`)}
              onMouseEnter={() => setHoveredFloor(floor.sessionId)}
              onMouseLeave={() => setHoveredFloor(null)}
            />
          ))}
        </svg>

        {/* 호버 레이블 */}
        {FLOORS.map((floor) =>
          hoveredFloor === floor.sessionId ? (
            <div
              key={`label-${floor.sessionId}`}
              style={{
                position: 'absolute',
                top: floor.labelTop,
                right: floor.labelRight,
                pointerEvents: 'none',
                zIndex: 10,
              }}
              className="rounded-lg bg-black/60 px-3 py-1 backdrop-blur-sm"
            >
              <span className="text-sm font-bold text-white">{floor.label} 세션 열기</span>
            </div>
          ) : null,
        )}
      </div>
    </div>
  )
}
