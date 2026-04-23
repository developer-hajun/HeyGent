import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Code,
  Calendar,
  Apple,
  Activity,
  Loader2,
  CheckCircle2,
  Bot,
  Zap,
  Clock,
  TrendingUp,
  X,
  Radio,
  ArrowRight,
  BarChart2,
  ListChecks,
  RefreshCw,
} from 'lucide-react'

const agents = [
  {
    id: 'code-review',
    name: '코드 리뷰 에이전트',
    shortName: 'Code Review',
    status: 'idle' as const,
    description: 'PR을 분석하고 버그, 보안 취약점 및 코드 품질 문제를 식별합니다.',
    tasksToday: 8,
    avgTime: '3.2분',
    successRate: 98,
    icon: Code,
    color: '#3b82f6',
    mapPos: { x: 24, y: 30 },
    currentTask: null as string | null,
    recentTasks: [
      { task: 'PR #245 — 보안 분석', time: '지금', status: 'running' as const },
      { task: 'PR #243 — 코드 품질', time: '5분 전', status: 'completed' as const },
      { task: 'PR #240 — 의존성 검토', time: '1시간 전', status: 'completed' as const },
    ],
  },
  {
    id: 'scheduler',
    name: '스케줄러 / 알림 에이전트',
    shortName: 'Scheduler',
    status: 'running' as const,
    description: '스마트 알림 생성, 일정 관리 및 시기적절한 알림을 전송합니다.',
    tasksToday: 15,
    avgTime: '0.8분',
    successRate: 100,
    icon: Calendar,
    color: '#8b5cf6',
    mapPos: { x: 72, y: 26 },
    currentTask: '오후 5시 회의 준비 알림' as string | null,
    recentTasks: [
      { task: '오후 5시 회의 준비 알림', time: '지금', status: 'running' as const },
      { task: '물 마시기 알림 (반복)', time: '30분 전', status: 'completed' as const },
      { task: '일일 스탠드업 설정', time: '어제', status: 'completed' as const },
    ],
  },
  {
    id: 'wellness',
    name: '식단 & 웰니스 에이전트',
    shortName: 'Wellness',
    status: 'ready' as const,
    description: '개인 맞춤형 식사 추천, 영양 추적 및 웰니스 인사이트를 제공합니다.',
    tasksToday: 4,
    avgTime: '1.5분',
    successRate: 95,
    icon: Apple,
    color: '#10b981',
    mapPos: { x: 26, y: 70 },
    currentTask: null as string | null,
    recentTasks: [
      { task: '저녁 메뉴 추천', time: '15분 전', status: 'completed' as const },
      { task: '칼로리 요약', time: '1시간 전', status: 'completed' as const },
      { task: '주간 식사 계획', time: '어제', status: 'completed' as const },
    ],
  },
  {
    id: 'health',
    name: '건강 데이터 컴패니언',
    shortName: 'Health',
    status: 'idle' as const,
    description: 'IoT 건강 기기를 모니터링하고 센서 데이터를 해석하며 웰니스 지표를 추적합니다.',
    tasksToday: 2,
    avgTime: '2.1분',
    successRate: 91,
    icon: Activity,
    color: '#f59e0b',
    mapPos: { x: 72, y: 68 },
    currentTask: null as string | null,
    recentTasks: [
      { task: '걸음 수 분석', time: '2시간 전', status: 'completed' as const },
      { task: '수면 품질 보고서', time: '어제', status: 'completed' as const },
      { task: '심박수 알림', time: '2일 전', status: 'completed' as const },
    ],
  },
]

const statusConfig = {
  running: {
    label: '실행 중',
    dot: 'bg-violet-500 animate-pulse',
    text: 'text-violet-600',
    badge: 'bg-violet-50 border-violet-200',
  },
  idle: {
    label: '대기 중',
    dot: 'bg-slate-400',
    text: 'text-slate-500',
    badge: 'bg-slate-50 border-slate-200',
  },
  ready: {
    label: '준비됨',
    dot: 'bg-emerald-500',
    text: 'text-emerald-600',
    badge: 'bg-emerald-50 border-emerald-200',
  },
}

function MapConnector({
  x1,
  y1,
  x2,
  y2,
  color,
  active,
}: {
  x1: number
  y1: number
  x2: number
  y2: number
  color: string
  active?: boolean
}) {
  return (
    <line
      x1={`${x1}%`}
      y1={`${y1}%`}
      x2={`${x2}%`}
      y2={`${y2}%`}
      stroke={color}
      strokeWidth={active ? 2 : 1}
      strokeDasharray={active ? '0' : '5 5'}
      strokeOpacity={active ? 0.55 : 0.2}
    />
  )
}

export function AgentStatusPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = agents.find((a) => a.id === selectedId) ?? null

  const handleSelect = (id: string) => {
    setSelectedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="bg-background relative flex-1 overflow-hidden">
      {/* ── Full-screen map ─────────────────────────────── */}
      <div className="absolute inset-0">
        {/* Dot-grid background */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle, rgba(148,163,184,0.35) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
        {/* Subtle vignette */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse at center, transparent 55%, rgba(241,245,249,0.6) 100%)',
          }}
        />

        {/* SVG connection lines */}
        <svg className="absolute inset-0 h-full w-full" style={{ zIndex: 1 }}>
          {agents.map((agent) => (
            <MapConnector
              key={agent.id}
              x1={50}
              y1={50}
              x2={agent.mapPos.x}
              y2={agent.mapPos.y}
              color={agent.color}
              active={agent.status === 'running' || selectedId === agent.id}
            />
          ))}
          {/* Agent–agent cross links */}
          <MapConnector
            x1={agents[0].mapPos.x}
            y1={agents[0].mapPos.y}
            x2={agents[1].mapPos.x}
            y2={agents[1].mapPos.y}
            color="#cbd5e1"
          />
          <MapConnector
            x1={agents[2].mapPos.x}
            y1={agents[2].mapPos.y}
            x2={agents[3].mapPos.x}
            y2={agents[3].mapPos.y}
            color="#cbd5e1"
          />
          <MapConnector
            x1={agents[1].mapPos.x}
            y1={agents[1].mapPos.y}
            x2={agents[3].mapPos.x}
            y2={agents[3].mapPos.y}
            color="#cbd5e1"
          />
          <MapConnector
            x1={agents[0].mapPos.x}
            y1={agents[0].mapPos.y}
            x2={agents[2].mapPos.x}
            y2={agents[2].mapPos.y}
            color="#cbd5e1"
          />
        </svg>

        {/* Center hub */}
        <div
          className="absolute z-10 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2"
          style={{ left: '50%', top: '50%' }}
        >
          {/* Outer pulse rings */}
          <div className="relative flex items-center justify-center">
            <span
              className="bg-primary/5 absolute h-24 w-24 animate-ping rounded-full"
              style={{ animationDuration: '3s' }}
            />
            <span
              className="bg-primary/8 absolute h-20 w-20 animate-ping rounded-full"
              style={{ animationDuration: '2.2s', animationDelay: '0.4s' }}
            />
            <div className="border-primary/25 relative flex h-16 w-16 items-center justify-center rounded-full border-2 bg-white shadow-xl">
              <Bot className="text-primary h-7 w-7" />
            </div>
          </div>
          <span className="text-foreground border-border rounded-full border bg-white/90 px-3 py-1 text-xs font-semibold whitespace-nowrap shadow-sm backdrop-blur-sm">
            Heygent AI
          </span>
        </div>

        {/* Agent nodes */}
        {agents.map((agent, i) => {
          const sc = statusConfig[agent.status]
          const isSelected = selectedId === agent.id
          return (
            <motion.button
              key={agent.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.15 + i * 0.08, type: 'spring', stiffness: 220, damping: 18 }}
              onClick={() => handleSelect(agent.id)}
              className="group absolute z-20 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
              style={{ left: `${agent.mapPos.x}%`, top: `${agent.mapPos.y}%` }}
            >
              {/* Running pulse */}
              {agent.status === 'running' && (
                <span
                  className="absolute inset-0 animate-ping rounded-2xl opacity-25"
                  style={{ backgroundColor: agent.color, borderRadius: '18px' }}
                />
              )}
              {/* Selection ring */}
              {isSelected && (
                <motion.span
                  layoutId="selection-ring"
                  className="absolute -inset-1.5 rounded-3xl"
                  style={{ border: `2px solid ${agent.color}`, borderRadius: '22px', opacity: 0.7 }}
                />
              )}
              <div
                className="relative flex min-w-[96px] flex-col items-center gap-2 rounded-2xl border bg-white px-4 py-3 shadow-lg transition-all group-hover:-translate-y-0.5 group-hover:shadow-xl"
                style={{
                  borderColor: isSelected ? agent.color : 'rgba(226,232,240,1)',
                  transition: 'border-color 0.15s, box-shadow 0.15s, transform 0.15s',
                }}
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ backgroundColor: `${agent.color}18` }}
                >
                  <agent.icon style={{ color: agent.color, width: '18px', height: '18px' }} />
                </div>
                <span className="text-foreground text-xs font-semibold whitespace-nowrap">
                  {agent.shortName}
                </span>
                <div
                  className={`flex items-center gap-1 rounded-full border px-2 py-0.5 ${sc.badge}`}
                >
                  <span className={`h-1.5 w-1.5 flex-shrink-0 rounded-full ${sc.dot}`} />
                  <span className={`text-xs font-medium ${sc.text}`} style={{ fontSize: '10px' }}>
                    {sc.label}
                  </span>
                </div>
                {/* Active task badge */}
                {agent.currentTask && (
                  <div
                    className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full shadow-md"
                    style={{ backgroundColor: agent.color }}
                  >
                    <Zap className="h-2.5 w-2.5 text-white" />
                  </div>
                )}
              </div>
            </motion.button>
          )
        })}

        {/* Top-left label */}
        <div className="absolute top-5 left-5 z-10 flex items-center gap-2">
          <div className="border-border flex items-center gap-1.5 rounded-lg border bg-white/90 px-3 py-1.5 shadow-sm backdrop-blur-sm">
            <Radio className="text-primary h-3.5 w-3.5 animate-pulse" />
            <span className="text-foreground text-xs font-semibold">에이전트 네트워크 맵</span>
          </div>
          <div className="border-border rounded-lg border bg-white/90 px-2.5 py-1.5 shadow-sm backdrop-blur-sm">
            <span className="text-muted-foreground text-xs">실시간 시각화</span>
          </div>
        </div>

        {/* Bottom legend */}
        <div className="absolute bottom-5 left-5 z-10 flex items-center gap-2">
          {[
            { color: '#8b5cf6', dotClass: 'animate-pulse', label: '실행 중' },
            { color: '#10b981', dotClass: '', label: '준비됨' },
            { color: '#94a3b8', dotClass: '', label: '대기 중' },
          ].map((l) => (
            <div
              key={l.label}
              className="border-border flex items-center gap-1.5 rounded-lg border bg-white/90 px-2.5 py-1.5 shadow-sm backdrop-blur-sm"
            >
              <span
                className={`h-2 w-2 flex-shrink-0 rounded-full ${l.dotClass}`}
                style={{ backgroundColor: l.color }}
              />
              <span className="text-muted-foreground text-xs">{l.label}</span>
            </div>
          ))}
        </div>

        {/* Hint when nothing selected */}
        <AnimatePresence>
          {!selected && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={{ delay: 0.6 }}
              className="border-border absolute right-5 bottom-5 z-10 rounded-lg border bg-white/90 px-3 py-1.5 shadow-sm backdrop-blur-sm"
            >
              <p className="text-muted-foreground text-xs">
                에이전트 노드를 클릭하면 상세 정보를 볼 수 있습니다
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ── Floating detail modal (RightPanel style) ─────── */}
      <AnimatePresence>
        {selected && (
          <motion.div
            key={selected.id}
            initial={{ opacity: 0, x: 20, scale: 0.97 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.97 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="border-border absolute top-1/2 right-5 z-30 w-72 -translate-y-1/2 overflow-hidden rounded-2xl border bg-white shadow-2xl"
            style={{ maxHeight: 'calc(100vh - 120px)' }}
          >
            {/* Modal header */}
            <div className="border-border flex flex-shrink-0 items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-2">
                <div
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${selected.color}18` }}
                >
                  <selected.icon style={{ color: selected.color, width: '14px', height: '14px' }} />
                </div>
                <div className="flex items-center gap-2">
                  <ListChecks className="text-primary h-3.5 w-3.5" />
                  <span className="text-foreground text-sm font-semibold">에이전트 상세</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedId(null)}
                className="hover:bg-muted text-muted-foreground flex h-6 w-6 items-center justify-center rounded-md transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Scrollable content */}
            <div className="overflow-y-auto" style={{ maxHeight: 'calc(100vh - 200px)' }}>
              <div className="space-y-4 p-4">
                {/* Identity */}
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl"
                    style={{ backgroundColor: `${selected.color}18` }}
                  >
                    <selected.icon
                      style={{ color: selected.color, width: '18px', height: '18px' }}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-foreground mb-1 text-sm leading-snug font-semibold">
                      {selected.name}
                    </h3>
                    <div
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${statusConfig[selected.status].badge} ${statusConfig[selected.status].text}`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${statusConfig[selected.status].dot}`}
                      />
                      {statusConfig[selected.status].label}
                    </div>
                  </div>
                </div>

                {/* Description */}
                <div className="bg-muted/40 rounded-xl p-3">
                  <p className="text-muted-foreground text-xs leading-relaxed">
                    {selected.description}
                  </p>
                </div>

                {/* Stats */}
                <div>
                  <p className="text-muted-foreground mb-2 text-xs font-semibold tracking-wide uppercase">
                    성과 지표
                  </p>
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="bg-muted flex h-6 w-6 items-center justify-center rounded-md">
                          <BarChart2 className="text-muted-foreground h-3 w-3" />
                        </div>
                        <span className="text-muted-foreground text-xs">오늘 처리 작업</span>
                      </div>
                      <span className="text-foreground text-sm font-semibold">
                        {selected.tasksToday}건
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="bg-muted flex h-6 w-6 items-center justify-center rounded-md">
                          <Clock className="text-muted-foreground h-3 w-3" />
                        </div>
                        <span className="text-muted-foreground text-xs">평균 처리 시간</span>
                      </div>
                      <span className="text-foreground text-sm font-semibold">
                        {selected.avgTime}
                      </span>
                    </div>
                    <div>
                      <div className="mb-1.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="bg-muted flex h-6 w-6 items-center justify-center rounded-md">
                            <TrendingUp className="text-muted-foreground h-3 w-3" />
                          </div>
                          <span className="text-muted-foreground text-xs">성공률</span>
                        </div>
                        <span className="text-foreground text-sm font-semibold">
                          {selected.successRate}%
                        </span>
                      </div>
                      <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${selected.successRate}%` }}
                          transition={{ duration: 0.65, ease: 'easeOut' }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: selected.color }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Current task */}
                {selected.currentTask && (
                  <div>
                    <p className="text-muted-foreground mb-2 text-xs font-semibold tracking-wide uppercase">
                      현재 작업
                    </p>
                    <div
                      className="flex items-center gap-2.5 rounded-xl border p-3"
                      style={{
                        borderColor: `${selected.color}35`,
                        backgroundColor: `${selected.color}08`,
                      }}
                    >
                      <Loader2
                        className="h-3.5 w-3.5 flex-shrink-0 animate-spin"
                        style={{ color: selected.color }}
                      />
                      <span className="text-foreground text-xs leading-snug font-medium">
                        {selected.currentTask}
                      </span>
                    </div>
                  </div>
                )}

                {/* Recent tasks */}
                <div>
                  <p className="text-muted-foreground mb-2 text-xs font-semibold tracking-wide uppercase">
                    최근 작업
                  </p>
                  <div className="space-y-1.5">
                    {selected.recentTasks.map((task, j) => (
                      <motion.div
                        key={j}
                        initial={{ opacity: 0, x: 8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: j * 0.05 }}
                        className="bg-muted/30 hover:bg-muted/50 flex items-start gap-2 rounded-lg p-2.5 transition-colors"
                      >
                        <div className="mt-0.5 flex-shrink-0">
                          {task.status === 'running' ? (
                            <Loader2 className="text-primary h-3 w-3 animate-spin" />
                          ) : (
                            <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-foreground text-xs leading-snug">{task.task}</p>
                          <p className="text-muted-foreground mt-0.5 text-xs">{task.time}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-2 pb-1">
                  <button
                    className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-semibold text-white transition-all hover:opacity-90 active:scale-[0.98]"
                    style={{ backgroundColor: selected.color }}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    에이전트 재시작
                  </button>
                  <button className="text-muted-foreground bg-muted hover:bg-muted/70 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-medium transition-colors">
                    작업 기록 전체 보기
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
