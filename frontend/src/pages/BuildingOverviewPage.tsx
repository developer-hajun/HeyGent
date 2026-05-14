import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router'
import { FloorAgentSprite } from '@/components/office/FloorAgentSprite'

const IMG_W = 1586
const IMG_H = 992

const VEHICLE_CSS = `
  @keyframes heygent-bike-move {
    0%     { transform: translateX(-600px); }
    35%    { transform: translateX(2000px); }
    35.01% { transform: translateX(-600px); }
    100%   { transform: translateX(-600px); }
  }
  @keyframes heygent-car-move {
    0%,    50%    { transform: translateX(-600px); }
    85%           { transform: translateX(2000px); }
    85.01%, 100%  { transform: translateX(-600px); }
  }
`

function VehicleLayer() {
  const [bikeFrame, setBikeFrame] = useState(1)
  useEffect(() => {
    const id = setInterval(() => setBikeFrame((f) => (f === 1 ? 2 : 1)), 250)
    return () => clearInterval(id)
  }, [])
  return (
    <>
      {/* 자전거: 스프라이트 프레임 전환하며 왼쪽→오른쪽 이동 (20s 주기 0~35%) */}
      <div
        style={{
          position: 'absolute',
          top: 893,
          left: 0,
          pointerEvents: 'none',
          zIndex: 20,
          animation: 'heygent-bike-move 30s linear infinite',
        }}
      >
        <img
          src={`/assets/maps/overview_bike_${bikeFrame}.png`}
          alt=""
          draggable={false}
          style={{ width: 135, height: 'auto', display: 'block' }}
        />
      </div>
      {/* 자동차: 자전거 이후 왼쪽→오른쪽 이동 (20s 주기 50~85%) */}
      <div
        style={{
          position: 'absolute',
          top: 873,
          left: 0,
          pointerEvents: 'none',
          zIndex: 20,
          animation: 'heygent-car-move 30s linear infinite',
        }}
      >
        <img
          src="/assets/maps/overview_car.png"
          alt=""
          draggable={false}
          style={{ width: 170, height: 'auto', display: 'block' }}
        />
      </div>
    </>
  )
}

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
    top: '13.7%',
    left: '20%',
    width: '61%',
    height: '24%',
    // SVG polygon matching the actual glass panel (within 1586×992 canvas)
    svgPoints: '326,178 1252,142 1290,157 1290,363 1252,358 326,375',
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

        {/* 차량 애니메이션: 건물 하단 도로 위를 오른쪽으로 이동 */}
        <style>{VEHICLE_CSS}</style>
        <VehicleLayer />
      </div>
    </div>
  )
}
