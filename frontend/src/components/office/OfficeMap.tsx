import { useRef, useEffect, useState } from 'react'
import { AgentSprite } from './AgentSprite'
import type { AgentRuntime } from './types'

const MAP_WIDTH = 1600
const MAP_HEIGHT = 900

const CEO_SPRITES = {
  desk: { src: '/assets/agents/ceo/ceo_desk.png', x: 310, y: 215, size: 230 },
  explain: { src: '/assets/agents/ceo/ceo_explain.png', x: 383, y: 493, size: 210 },
}

interface OfficeMapProps {
  agents: AgentRuntime[]
  onAgentArrived: (agentId: string) => void
  ceoMode: 'desk' | 'explain' | null
}

export function OfficeMap({ agents, onAgentArrived, ceoMode }: OfficeMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [debugCoord, setDebugCoord] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      const s = Math.min(width / MAP_WIDTH, height / MAP_HEIGHT)
      setScale(s)
      setOffset({
        x: Math.max(0, (width - MAP_WIDTH * s) / 2),
        y: Math.max(0, (height - MAP_HEIGHT * s) / 2),
      })
    })

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return

    // 스크린 좌표 → 맵 좌표 역변환 (offset 제거 후 scale 나누기)
    const mapX = Math.round((e.clientX - rect.left - offset.x) / scale)
    const mapY = Math.round((e.clientY - rect.top - offset.y) / scale)

    console.log(`맵 좌표: { x: ${mapX}, y: ${mapY} }`)
    setDebugCoord({ x: mapX, y: mapY })
  }

  return (
    <div
      ref={containerRef}
      className="relative flex-1 cursor-crosshair overflow-hidden bg-gray-900"
      onClick={handleMapClick}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: MAP_WIDTH,
          height: MAP_HEIGHT,
          transformOrigin: 'top left',
          transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
        }}
      >
        <img
          src="/assets/maps/office_map.png"
          alt="Office Map"
          draggable={false}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            display: 'block',
          }}
        />
        {agents.map((agent) => (
          <AgentSprite key={agent.config.id} agent={agent} onArrived={onAgentArrived} />
        ))}
        {ceoMode &&
          (() => {
            const sprite = CEO_SPRITES[ceoMode]
            return (
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: sprite.size,
                  height: sprite.size,
                  transform: `translate(${sprite.x - sprite.size / 2}px, ${sprite.y - sprite.size / 2}px)`,
                  zIndex: 10,
                  pointerEvents: 'none',
                }}
              >
                <img
                  src={sprite.src}
                  alt="CEO"
                  draggable={false}
                  style={{ width: '100%', height: '100%', userSelect: 'none' }}
                />
              </div>
            )
          })()}
      </div>

      {/* 클릭 좌표 디버그 오버레이 */}
      {debugCoord && (
        <div className="absolute top-4 left-1/2 z-30 -translate-x-1/2">
          <div className="flex items-center gap-3 rounded-xl border border-white/20 bg-black/70 px-4 py-2 shadow-xl backdrop-blur-md">
            <span className="font-mono text-sm text-yellow-300">
              x: {debugCoord.x}, y: {debugCoord.y}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setDebugCoord(null)
              }}
              className="text-xs text-white/50 hover:text-white"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
