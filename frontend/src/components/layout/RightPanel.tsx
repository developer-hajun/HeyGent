import { useRef, useState, useCallback, useMemo } from 'react'
import { X, MoreVertical, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSessionStore, type AgentPanelItem } from '@/store/useSessionStore'
export type { Agent } from '@/types/agent'

const TAB_H = 96
const TAB_GAP = 12
const MIN_SPACING = TAB_H + TAB_GAP

/** 모든 탭이 겹치지 않도록 정렬. 드래그 종료 후 호출.
 *  pinnedId: 드래그한 탭 — 위치를 고정하고 나머지만 밀어냄. */
function resolveAll(
  offsets: Map<string, number>,
  ids: string[],
  pinnedId?: string,
): Map<string, number> {
  const result = new Map(offsets)
  const halfH = window.innerHeight / 2

  for (let pass = 0; pass < 20; pass++) {
    let changed = false
    const sorted = [...ids].sort((a, b) => (result.get(a) ?? 0) - (result.get(b) ?? 0))
    for (let i = 1; i < sorted.length; i++) {
      const above = sorted[i - 1]
      const below = sorted[i]
      const gap = (result.get(below) ?? 0) - (result.get(above) ?? 0)
      if (gap < MIN_SPACING) {
        const abovePinned = above === pinnedId
        const belowPinned = below === pinnedId
        if (abovePinned) {
          // above가 드래그한 탭 → above만 밀어냄 (below 고정)
          result.set(above, (result.get(below) ?? 0) - MIN_SPACING)
        } else if (belowPinned) {
          // below가 드래그한 탭 → below만 밀어냄 (above 고정)
          result.set(below, (result.get(above) ?? 0) + MIN_SPACING)
        } else {
          // 둘 다 비고정 → 중간점 기준 분리
          const mid = ((result.get(above) ?? 0) + (result.get(below) ?? 0)) / 2
          result.set(above, mid - MIN_SPACING / 2)
          result.set(below, mid + MIN_SPACING / 2)
        }
        changed = true
      }
    }
    if (!changed) break
  }

  // 화면 밖으로 나간 탭 클램핑
  for (const [id, y] of result) {
    const clamped = Math.max(-halfH + TAB_H / 2, Math.min(halfH - TAB_H / 2, y))
    if (clamped !== y) result.set(id, clamped)
  }

  return result
}

// ── 개별 에이전트 탭 ──────────────────────────────────────────────
interface AgentTabProps {
  item: AgentPanelItem
  offsetY: number
  onDragMove: (id: string, y: number) => void
  onDragEnd: () => void
}

function AgentTab({ item, offsetY, onDragMove, onDragEnd }: AgentTabProps) {
  const { removeAgentPanel, toggleAgentPanel } = useSessionStore()
  const dragStartY = useRef(0)
  const hasDragged = useRef(false)
  const [active, setActive] = useState(false)

  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    hasDragged.current = false
    dragStartY.current = e.clientY - offsetY
    const halfH = window.innerHeight / 2
    const onMove = (ev: MouseEvent) => {
      if (!hasDragged.current) {
        hasDragged.current = true
        setActive(true)
      }
      const next = ev.clientY - dragStartY.current
      onDragMove(item.id, Math.max(-halfH + TAB_H / 2, Math.min(halfH - TAB_H / 2, next)))
    }
    const onUp = () => {
      setActive(false)
      onDragEnd()
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      // hasDragged는 onClick 이후 리셋 (setTimeout으로 onClick보다 늦게 실행)
      setTimeout(() => {
        hasDragged.current = false
      }, 0)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  return (
    <div
      className="pointer-events-auto fixed z-50 flex items-center select-none"
      style={{
        right: 'var(--scrollbar-width, 0px)',
        top: '50%',
        transform: `translateY(calc(-50% + ${offsetY}px))`,
        transition: active ? 'none' : 'transform 0.2s ease',
      }}
    >
      <AnimatePresence>
        {item.panelOpen && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, x: 16, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 16, scale: 0.97 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="border-border mr-2 w-64 overflow-hidden rounded-xl border bg-white shadow-xl"
          >
            <div className="border-border flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-2">
                <item.agent.icon className="h-4 w-4" style={{ color: item.agent.accent }} />
                <span className="text-foreground text-sm font-semibold">{item.agent.name}</span>
              </div>
              <div className="flex items-center gap-1">
                <Popover>
                  <PopoverTrigger asChild>
                    <button className="hover:bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-md transition-colors">
                      <MoreVertical className="h-3.5 w-3.5" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent className="w-48 rounded-xl p-1.5" align="end">
                    <button
                      onClick={() => removeAgentPanel(item.id)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-red-600 transition-colors hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                      <span className="text-sm font-medium">목록에서 삭제</span>
                    </button>
                  </PopoverContent>
                </Popover>
                <button
                  onClick={() => toggleAgentPanel(item.id)}
                  className="hover:bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-md transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="p-4">
              <p className="text-muted-foreground mb-4 text-sm">{item.agent.description}</p>
              <div className="space-y-2">
                <button
                  className="w-full rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
                  style={{ backgroundColor: item.agent.accent }}
                >
                  실행하기
                </button>
                <button className="bg-muted text-foreground hover:bg-muted/80 w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors">
                  설정
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onMouseDown={startDrag}
        onClick={() => {
          if (!hasDragged.current) toggleAgentPanel(item.id)
        }}
        className={`relative flex h-24 w-9 cursor-grab flex-col items-center justify-center gap-1.5 rounded-l-xl border border-r-0 shadow-md transition-all duration-150 active:cursor-grabbing ${
          item.panelOpen
            ? 'border-transparent text-white'
            : 'border-border text-muted-foreground bg-white hover:bg-gray-50'
        }`}
        style={
          item.panelOpen
            ? { backgroundColor: item.agent.accent, borderColor: item.agent.accent }
            : undefined
        }
      >
        <item.agent.icon className="h-4 w-4 shrink-0" />
        <span
          className="shrink-0 text-xs font-medium"
          style={{ writingMode: 'vertical-rl', textOrientation: 'upright', fontSize: '10px' }}
        >
          {item.agent.name}
        </span>
      </button>
    </div>
  )
}

// ── 진입점 ────────────────────────────────────────────────────────
export function RightPanel() {
  const { agentPanels } = useSessionStore()
  const [offsets, setOffsets] = useState<Map<string, number>>(() => new Map())

  const panelIdKey = agentPanels.map((p) => p.id).join(',')
  const allIds = useMemo(
    () => agentPanels.map((p) => p.id),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [panelIdKey],
  )

  // 새 탭 추가 시 겹치지 않는 초기 위치 배정
  for (const id of allIds) {
    if (!offsets.has(id)) {
      const existing = [...offsets.values()].sort((a, b) => a - b)
      let candidate = 0
      for (const oy of existing) {
        if (Math.abs(candidate - oy) < MIN_SPACING) candidate = oy + MIN_SPACING
      }
      offsets.set(id, candidate)
    }
  }
  for (const id of offsets.keys()) {
    if (!allIds.includes(id)) offsets.delete(id)
  }

  const lastDraggedId = useRef<string | undefined>(undefined)

  // 드래그 중: 겹침 허용하고 raw 위치만 업데이트
  const handleDragMove = useCallback((draggedId: string, nextY: number) => {
    lastDraggedId.current = draggedId
    setOffsets((prev) => new Map(prev).set(draggedId, nextY))
  }, [])

  // 드래그 종료: 겹침 해소 + 화면 경계 클램핑 (드래그한 탭 위치 고정)
  const handleDragEnd = useCallback(() => {
    setOffsets((prev) => resolveAll(prev, allIds, lastDraggedId.current))
  }, [allIds])

  return (
    <>
      {agentPanels.map((item) => (
        <AgentTab
          key={item.id}
          item={item}
          offsetY={offsets.get(item.id) ?? 0}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
        />
      ))}
    </>
  )
}
