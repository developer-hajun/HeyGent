import type { ComponentType, CSSProperties } from 'react'
import { Calendar, X, Clock, AlertCircle, MoreVertical, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useUIStore } from '@/store/useUIStore'
import { useSessionStore } from '@/store/useSessionStore'

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

export function RightPanel() {
  const { rightPanelType, toggleRightPanel, setRightPanelType } = useUIStore()
  const { selectedAgent, clearSelectedAgent } = useSessionStore()

  const urgentCount = upcomingReminders.filter((r) => r.urgent).length

  return (
    <div className="pointer-events-none fixed top-1/2 right-0 z-50 flex -translate-y-1/2 flex-col items-end gap-3">
      {/* ── Schedule Panel ── */}
      <div className="pointer-events-auto flex items-center gap-0">
        <AnimatePresence>
          {rightPanelType === 'schedule' && (
            <motion.div
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
                        <AlertCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-orange-500" />
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
          onClick={() => toggleRightPanel('schedule')}
          className={`relative flex h-24 w-9 flex-col items-center justify-center gap-1.5 rounded-l-xl border border-r-0 shadow-md transition-all duration-150 ${
            rightPanelType === 'schedule'
              ? 'bg-primary border-primary shadow-primary/20 text-white'
              : 'text-muted-foreground border-border hover:text-primary bg-white hover:border-blue-200 hover:bg-blue-50'
          }`}
        >
          <Calendar className="h-4 w-4 flex-shrink-0" />
          <span
            className="flex-shrink-0 text-xs font-medium"
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

      {/* ── Agent Panel ── */}
      {selectedAgent && (
        <div className="pointer-events-auto flex items-center gap-0">
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, x: 16, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 16, scale: 0.97 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="border-border mr-2 w-64 overflow-hidden rounded-xl border bg-white shadow-xl"
            >
              <div className="border-border flex items-center justify-between border-b px-4 py-3">
                <div className="flex items-center gap-2">
                  <selectedAgent.icon className="h-4 w-4" style={{ color: selectedAgent.accent }} />
                  <span className="text-foreground text-sm font-semibold">
                    {selectedAgent.name}
                  </span>
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
                        onClick={clearSelectedAgent}
                        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-red-600 transition-colors hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="text-sm font-medium">목록에서 삭제</span>
                      </button>
                    </PopoverContent>
                  </Popover>
                  <button
                    onClick={clearSelectedAgent}
                    className="hover:bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-md transition-colors"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <div className="p-4">
                <p className="text-muted-foreground mb-4 text-sm">{selectedAgent.description}</p>
                <div className="space-y-2">
                  <button
                    className="w-full rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
                    style={{ backgroundColor: selectedAgent.accent }}
                  >
                    실행하기
                  </button>
                  <button className="bg-muted text-foreground hover:bg-muted/80 w-full rounded-lg px-4 py-2 text-sm font-medium transition-colors">
                    설정
                  </button>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>

          <button
            onClick={clearSelectedAgent}
            className="text-muted-foreground border-border hover:bg-muted/30 relative flex h-24 w-9 flex-col items-center justify-center gap-1.5 rounded-l-xl border border-r-0 bg-white shadow-md transition-all duration-150"
            style={{
              backgroundColor: `${selectedAgent.accent}14`,
              borderColor: selectedAgent.accent,
            }}
          >
            <selectedAgent.icon
              className="h-4 w-4 flex-shrink-0"
              style={{ color: selectedAgent.accent }}
            />
            <span
              className="flex-shrink-0 text-xs font-medium"
              style={{
                writingMode: 'vertical-rl',
                textOrientation: 'upright',
                fontSize: '10px',
                color: selectedAgent.accent,
              }}
            >
              {selectedAgent.name}
            </span>
          </button>
        </div>
      )}
    </div>
  )
}
