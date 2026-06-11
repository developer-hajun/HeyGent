import { useEffect, useRef } from 'react'

interface Props {
  agentId: string
  initialXPct: number
  size?: number
  bottomPct?: number
  minXPct?: number
  maxXPct?: number
}

const WALK_SPRITES = ['walk_side_01.png', 'walk_side_02.png'] as const
const IDLE_SPRITE = 'walk_side_stand.png'
const WALK_SPEED = 20 // px/s
const FRAME_MS = 280 // ms per walk frame

export function FloorAgentSprite({
  agentId,
  initialXPct,
  size = 82,
  bottomPct = 8,
  minXPct = 2,
  maxXPct = 88,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    const initDir = Math.random() > 0.5 ? 1 : (-1 as 1 | -1)
    const clampedX = Math.max(initialXPct, minXPct)
    const state = {
      x: clampedX,
      dir: initDir,
      frameIdx: 0 as 0 | 1,
      pauseUntil: 0,
      isPaused: false,
      lastFrameTime: 0,
      prevTime: 0,
    }

    if (imgRef.current) {
      imgRef.current.style.transform = initDir === 1 ? 'scaleX(-1)' : 'scaleX(1)'
    }

    let rafId: number

    const tick = (ts: number) => {
      if (state.prevTime === 0) {
        state.prevTime = ts
        state.lastFrameTime = ts
        rafId = requestAnimationFrame(tick)
        return
      }

      const dt = Math.min(ts - state.prevTime, 50)
      state.prevTime = ts

      const wrap = wrapRef.current
      const img = imgRef.current
      if (!wrap || !img) {
        rafId = requestAnimationFrame(tick)
        return
      }

      const parentW = wrap.parentElement?.clientWidth ?? 400
      const agentWidthPct = (size / parentW) * 100
      const minX = minXPct
      const maxX = maxXPct - agentWidthPct

      if (ts < state.pauseUntil) {
        if (!state.isPaused) {
          state.isPaused = true
          img.src = `/assets/agents/${agentId}/${IDLE_SPRITE}`
        }
        rafId = requestAnimationFrame(tick)
        return
      }

      if (state.isPaused) {
        state.isPaused = false
        state.lastFrameTime = ts
        img.src = `/assets/agents/${agentId}/${WALK_SPRITES[state.frameIdx]}`
      }

      const pctPerMs = ((WALK_SPEED / parentW) * 100) / 1000
      state.x += state.dir * pctPerMs * dt

      if (state.x >= maxX) {
        state.x = maxX
        state.dir = -1
      } else if (state.x <= minX) {
        state.x = minX
        state.dir = 1
      }

      img.style.transform = state.dir === 1 ? 'scaleX(-1)' : 'scaleX(1)'

      if (Math.random() < 0.0004 * dt) {
        state.pauseUntil = ts + 600 + Math.random() * 1800
      }

      if (ts - state.lastFrameTime > FRAME_MS) {
        state.lastFrameTime = ts
        state.frameIdx = ((state.frameIdx + 1) % 2) as 0 | 1
        img.src = `/assets/agents/${agentId}/${WALK_SPRITES[state.frameIdx]}`
      }

      wrap.style.left = `${state.x}%`
      rafId = requestAnimationFrame(tick)
    }

    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
  }, [agentId, size, initialXPct, maxXPct, minXPct])

  return (
    <div
      ref={wrapRef}
      style={{
        position: 'absolute',
        bottom: `${bottomPct}%`,
        left: `${Math.max(initialXPct, minXPct)}%`,
        width: size,
        height: size,
        pointerEvents: 'none',
      }}
    >
      <img
        ref={imgRef}
        src={`/assets/agents/${agentId}/${WALK_SPRITES[0]}`}
        alt={agentId}
        draggable={false}
        style={{ width: '100%', height: '100%', objectFit: 'contain', userSelect: 'none' }}
      />
    </div>
  )
}
