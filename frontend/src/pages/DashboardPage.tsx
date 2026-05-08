import { Server, Wifi, Bot, Eye, Plus, LayoutList } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router'
import { useUIStore } from '@/store/useUIStore'

type ServerStatus = 'ok' | 'error'
type IotStatus = 'connected' | 'unregistered' | 'inactive'
type AgentStatus = 'idle' | 'working'

// UI 전용 목업 상태 — API 연동 시 교체
const MOCK_SERVER: ServerStatus = 'ok'
const MOCK_IOT: IotStatus = 'connected'
const MOCK_AGENT: AgentStatus = 'idle'

interface StatusDotProps {
  color: 'emerald' | 'red' | 'amber' | 'muted' | 'blue'
  pulse?: boolean
}

function StatusDot({ color, pulse }: StatusDotProps) {
  const colorClass = {
    emerald: 'bg-emerald-500',
    red: 'bg-red-500',
    amber: 'bg-amber-400',
    muted: 'bg-muted-foreground/50',
    blue: 'bg-blue-500',
  }[color]

  return (
    <span className="relative flex h-2 w-2 shrink-0 items-center justify-center">
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${colorClass}`}
        />
      )}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${colorClass}`} />
    </span>
  )
}

interface StatusCardProps {
  icon: React.ReactNode
  title: string
  statusLabel: string
  dotColor: StatusDotProps['color']
  pulse?: boolean
}

function StatusCard({ icon, title, statusLabel, dotColor, pulse }: StatusCardProps) {
  return (
    <div className="border-border bg-card flex flex-col gap-3 rounded-xl border p-4">
      <div className="text-muted-foreground bg-muted/60 flex h-8 w-8 items-center justify-center rounded-lg">
        {icon}
      </div>
      <div className="space-y-1">
        <p className="text-muted-foreground text-xs">{title}</p>
        <div className="flex items-center gap-1.5">
          <StatusDot color={dotColor} pulse={pulse} />
          <span className="text-foreground text-sm font-medium">{statusLabel}</span>
        </div>
      </div>
    </div>
  )
}

interface ActionButtonProps {
  icon: React.ReactNode
  label: string
  onClick: () => void
}

function ActionButton({ icon, label, onClick }: ActionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-border bg-card hover:bg-accent/50 group flex flex-col items-start gap-3 rounded-xl border p-4 transition-colors"
    >
      <div className="text-muted-foreground group-hover:text-foreground bg-muted/60 flex h-8 w-8 items-center justify-center rounded-lg transition-colors">
        {icon}
      </div>
      <span className="text-foreground text-sm font-medium">{label}</span>
    </button>
  )
}

function serverStatusConfig(s: ServerStatus) {
  return s === 'ok'
    ? { label: '정상', color: 'emerald' as const }
    : { label: '오류', color: 'red' as const }
}

function iotStatusConfig(s: IotStatus) {
  if (s === 'connected') return { label: '연결됨', color: 'emerald' as const }
  if (s === 'unregistered') return { label: '미등록', color: 'muted' as const }
  return { label: '비활성', color: 'amber' as const }
}

function agentStatusConfig(s: AgentStatus) {
  return s === 'idle'
    ? { label: '대기 중', color: 'muted' as const, pulse: false }
    : { label: '작업 중', color: 'blue' as const, pulse: true }
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { setSidebarCollapsed } = useUIStore()

  const server = serverStatusConfig(MOCK_SERVER)
  const iot = iotStatusConfig(MOCK_IOT)
  const agent = agentStatusConfig(MOCK_AGENT)

  const handleShowSessions = () => {
    setSidebarCollapsed(false)
  }

  return (
    <div className="bg-background flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-8 px-6 py-10">
        {/* 섹션: 연결 및 에이전트 상태 */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            시스템 상태
          </p>
          <div className="grid grid-cols-3 gap-3">
            <StatusCard
              icon={<Server className="h-4 w-4" />}
              title="서버 연결"
              statusLabel={server.label}
              dotColor={server.color}
            />
            <StatusCard
              icon={<Wifi className="h-4 w-4" />}
              title="IoT 연결"
              statusLabel={iot.label}
              dotColor={iot.color}
            />
            <StatusCard
              icon={<Bot className="h-4 w-4" />}
              title="에이전트"
              statusLabel={agent.label}
              dotColor={agent.color}
              pulse={agent.pulse}
            />
          </div>
        </motion.section>

        {/* 구분선 */}
        <div className="border-border border-t" />

        {/* 섹션: 빠른 실행 */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            빠른 실행
          </p>
          <div className="grid grid-cols-3 gap-3">
            <ActionButton
              icon={<Eye className="h-4 w-4" />}
              label="에이전트 시각화 보기"
              onClick={() => navigate('/agent-status')}
            />
            <ActionButton
              icon={<Plus className="h-4 w-4" />}
              label="새 작업 요청하기"
              onClick={() => navigate('/new-chat')}
            />
            <ActionButton
              icon={<LayoutList className="h-4 w-4" />}
              label="세션 목록 보기"
              onClick={handleShowSessions}
            />
          </div>
        </motion.section>
      </div>
    </div>
  )
}
