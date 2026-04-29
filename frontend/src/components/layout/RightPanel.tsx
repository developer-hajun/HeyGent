import type { ComponentType, CSSProperties } from 'react'
import { useRef, useState, useCallback, useMemo } from 'react'
import { Calendar, X, Clock, AlertCircle, MoreVertical, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useUIStore } from '@/store/useUIStore'
import { useSessionStore, type AgentPanelItem } from '@/store/useSessionStore'

const upcomingReminders = [
  { id: 1, title: '팀 회의 준비', time: '1시간 30분 후', type: '일정', urgent: false },
  { id: 2, title: '물 마시기', time: '30분 후', type: '반복', urgent: true },
  { id: 3, title: '프로틴 섭취', time: '2시간 후', type: '할 일', urgent: false },
  { id: 4, title: '데일리 스탠드업', time: '내일 오전 10시', type: '반복', urgent: false },
]

const typeColors: Record<string, string> = {
  일정: 'bg-blue-50 text-blue-600',
  반복: 'bg-emerald-50 text-emerald-600',
  '할 일': 'bg-violet-50 text-violet-600',
}

export interface Agent {
  name: string
  icon: ComponentType<{ className?: string; style?: CSSProperties }>
  accent: string
  description: string
}

const TAB_H = 96
const TAB_GAP = 12
const MIN_SPACING = TAB_H + TAB_GAP

/** 모든 탭이 겹치지 않도록 정렬. 드래그 종료 후 호출. */
function resolveAll(offsets: Map<string, number>, ids: string[]): Map<string, number> {
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
        const mid = ((result.get(above) ?? 0) + (result.get(below) ?? 0)) / 2
        result.set(above, mid - MIN_SPACING / 2)
        result.set(below, mid + MIN_SPACING / 2)
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
  const isDragging = useRef(false)
  const [active, setActive] = useState(false)

  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = false
    dragStartY.current = e.clientY - offsetY
    const halfH = window.innerHeight / 2
    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current) {
        isDragging.current = true
        setActive(true)
      }
      const next = ev.clientY - dragStartY.current
      onDragMove(item.id, Math.max(-halfH + TAB_H / 2, Math.min(halfH - TAB_H / 2, next)))
    }
    const onUp = () => {
      isDragging.current = false
      setActive(false)
      onDragEnd()
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
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
          if (!isDragging.current) toggleAgentPanel(item.id)
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

// ── 일정 탭 ──────────────────────────────────────────────────────
interface ScheduleTabProps {
  offsetY: number
  onDragMove: (id: string, y: number) => void
  onDragEnd: () => void
}

function ScheduleTab({ offsetY, onDragMove, onDragEnd }: ScheduleTabProps) {
  const { rightPanelType, toggleRightPanel, setRightPanelType } = useUIStore()
  const dragStartY = useRef(0)
  const isDragging = useRef(false)
  const [active, setActive] = useState(false)
  const urgentCount = upcomingReminders.filter((r) => r.urgent).length

  const startDrag = (e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = false
    dragStartY.current = e.clientY - offsetY
    const halfH = window.innerHeight / 2
    const onMove = (ev: MouseEvent) => {
      if (!isDragging.current) {
        isDragging.current = true
        setActive(true)
      }
      const next = ev.clientY - dragStartY.current
      onDragMove('schedule', Math.max(-halfH + TAB_H / 2, Math.min(halfH - TAB_H / 2, next)))
    }
    const onUp = () => {
      isDragging.current = false
      setActive(false)
      onDragEnd()
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
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
        {rightPanelType === 'schedule' && (
          <motion.div
            key="schedule-panel"
            initial={{ opacity: 0, x: 16, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 16, scale: 0.97 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="border-border mr-2 w-64 overflow-hidden rounded-xl border bg-white shadow-xl"
          >
            <div className="border-border flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-2">
                <Calendar className="text-primary h-4 w-4" />
                <span className="text-foreground text-sm font-semibold">일정</span>
                {urgentCount > 0 && (
                  <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-600">
                    {urgentCount}개 임박
                  </span>
                )}
              </div>
              <button
                onClick={() => setRightPanelType(null)}
                className="hover:bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-md transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="max-h-72 space-y-2 overflow-y-auto p-3">
              {upcomingReminders.map((reminder) => (
                <div
                  key={reminder.id}
                  className={`rounded-lg border p-3 transition-colors ${
                    reminder.urgent
                      ? 'border-orange-200 bg-orange-50/60'
                      : 'border-border bg-muted/30 hover:bg-muted/50'
                  }`}
                >
                  <div className="mb-1.5 flex items-start justify-between gap-2">
                    <p className="text-foreground flex-1 text-sm leading-snug font-medium">
                      {reminder.title}
                    </p>
                    {reminder.urgent && (
                      <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-500" />
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <Clock className="text-primary h-3 w-3" />
                      <span className="text-primary text-xs font-medium">{reminder.time}</span>
                    </div>
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-xs font-medium ${typeColors[reminder.type]}`}
                    >
                      {reminder.type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onMouseDown={startDrag}
        onClick={() => {
          if (!isDragging.current) toggleRightPanel('schedule')
        }}
        className={`relative flex h-24 w-9 cursor-grab flex-col items-center justify-center gap-1.5 rounded-l-xl border border-r-0 shadow-md transition-all duration-150 active:cursor-grabbing ${
          rightPanelType === 'schedule'
            ? 'bg-primary border-primary shadow-primary/20 text-white'
            : 'text-muted-foreground border-border hover:text-primary bg-white hover:border-blue-200 hover:bg-blue-50'
        }`}
      >
        <Calendar className="h-4 w-4 shrink-0" />
        <span
          className="shrink-0 text-xs font-medium"
          style={{ writingMode: 'vertical-rl', textOrientation: 'upright', fontSize: '10px' }}
        >
          일정
        </span>
        {urgentCount > 0 && rightPanelType !== 'schedule' && (
          <span
            className="absolute -top-1 -left-1 flex h-4 w-4 items-center justify-center rounded-full bg-orange-500 text-xs font-bold text-white"
            style={{ fontSize: '9px' }}
          >
            {urgentCount}
          </span>
        )}
      </button>
    </div>
  )
}

// ── 진입점 ────────────────────────────────────────────────────────
export function RightPanel() {
  const { agentPanels } = useSessionStore()
  const [offsets, setOffsets] = useState<Map<string, number>>(() => new Map([['schedule', 0]]))

  const panelIdKey = agentPanels.map((p) => p.id).join(',')
  const allIds = useMemo(
    () => ['schedule', ...agentPanels.map((p) => p.id)],
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

  // 드래그 중: 겹침 허용하고 raw 위치만 업데이트
  const handleDragMove = useCallback((draggedId: string, nextY: number) => {
    setOffsets((prev) => new Map(prev).set(draggedId, nextY))
  }, [])

  // 드래그 종료: 겹침 해소 + 화면 경계 클램핑
  const handleDragEnd = useCallback(() => {
    setOffsets((prev) => resolveAll(prev, allIds))
  }, [allIds])

  return (
    <>
      <ScheduleTab
        offsetY={offsets.get('schedule') ?? 0}
        onDragMove={handleDragMove}
        onDragEnd={handleDragEnd}
      />
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
