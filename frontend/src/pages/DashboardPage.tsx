import { useEffect, useState, useCallback } from 'react'
import { Server, Wifi, Bot, Eye, Plus, Loader2, KeyRound } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router'
import { useUIStore } from '@/store/useUIStore'
import { getIotDevices, deleteIotDevice, pairIotDevice, type IotDevice } from '@/apis/iot'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { NewSessionModal, type CustomAgentConfig } from '@/components/session/NewSessionModal'

// ── Mock 상태 (서버·에이전트) ─────────────────────────────────────────────────
type ServerStatus = 'ok' | 'error'
type AgentStatus = 'idle' | 'working'

const MOCK_SERVER: ServerStatus = 'ok'
const MOCK_AGENT: AgentStatus = 'idle'

// ── StatusDot ────────────────────────────────────────────────────────────────
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

// ── StatusCard ───────────────────────────────────────────────────────────────
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
      <div className="flex items-center gap-2">
        <div className="text-muted-foreground bg-muted/60 flex h-8 w-8 items-center justify-center rounded-lg">
          {icon}
        </div>
        <p className="text-muted-foreground text-xs">{title}</p>
      </div>
      <div className="flex items-center gap-1.5">
        <StatusDot color={dotColor} pulse={pulse} />
        <span className="text-foreground text-sm font-medium">{statusLabel}</span>
      </div>
    </div>
  )
}

// ── IotCard ──────────────────────────────────────────────────────────────────
function formatLastSeen(lastSeenAt: string | null): string {
  if (!lastSeenAt) return '-'
  return new Date(lastSeenAt).toLocaleString('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface IotCardProps {
  loading: boolean
  device: IotDevice | null
  onRegister: () => void
  onDeregister: (deviceId: string) => void
}

function IotCard({ loading, device, onRegister, onDeregister }: IotCardProps) {
  const isActive = device?.status === 'ACTIVE'

  return (
    <div className="border-border bg-card rounded-xl border p-4">
      <div className="mb-3 flex items-center gap-2">
        <div className="text-muted-foreground bg-muted/60 flex h-8 w-8 items-center justify-center rounded-lg">
          <Wifi className="h-4 w-4" />
        </div>
        <p className="text-muted-foreground text-xs">IoT 연결</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 py-1">
          <Loader2 className="text-muted-foreground h-3.5 w-3.5 animate-spin" />
          <span className="text-muted-foreground text-xs">기기 정보를 불러오는 중...</span>
        </div>
      )}

      {!loading && !device && (
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground text-sm">등록된 디바이스가 없습니다.</span>
          <button
            type="button"
            onClick={onRegister}
            className="border-border text-foreground hover:bg-accent/50 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors"
          >
            기기 등록하기
          </button>
        </div>
      )}

      {!loading && device && (
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-0.5">
              <p className="text-foreground text-sm font-medium">
                {device.displayName ?? '(이름 없음)'}
              </p>
              <p className="text-muted-foreground font-mono text-xs">{device.deviceId}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5 pt-0.5">
              <StatusDot color={isActive ? 'emerald' : 'amber'} />
              <span className="text-foreground text-xs font-medium">
                {isActive ? '연결됨' : '비활성'}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground text-xs">마지막 접속</span>
              <span className="text-foreground text-xs">{formatLastSeen(device.lastSeenAt)}</span>
            </div>
            <button
              type="button"
              onClick={() => onDeregister(device.deviceId)}
              className="text-xs font-medium text-red-500 transition-colors hover:text-red-600"
            >
              등록 해제
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── DeregisterConfirmModal ────────────────────────────────────────────────────
interface DeregisterConfirmModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => Promise<void>
}

function DeregisterConfirmModal({ open, onOpenChange, onConfirm }: DeregisterConfirmModalProps) {
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm gap-5">
        <div>
          <DialogTitle className="text-base">기기 등록을 해제할까요?</DialogTitle>
          <DialogDescription className="text-muted-foreground mt-2 text-sm leading-relaxed">
            등록 해제하면 현재 계정과 디바이스의 연결이 끊어집니다.
            <br />
            다시 사용하려면 페어링 코드를 입력해 재등록해야 합니다.
          </DialogDescription>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="border-border text-foreground hover:bg-accent/50 flex-1 rounded-xl border py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className="flex-1 rounded-xl bg-red-500 py-2.5 text-sm font-medium text-white transition-colors hover:bg-red-600 disabled:opacity-50"
          >
            {loading ? '해제 중...' : '등록 해제'}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── PairingModal ─────────────────────────────────────────────────────────────
interface PairingModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (device: IotDevice) => void
}

function PairingModal({ open, onOpenChange, onSuccess }: PairingModalProps) {
  const [pairCode, setPairCode] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [codeError, setCodeError] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const resetForm = () => {
    setPairCode('')
    setDisplayName('')
    setCodeError(null)
    setApiError(null)
  }

  const handlePairCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6)
    setPairCode(value)
    if (codeError) setCodeError(null)
  }

  const validate = (): boolean => {
    if (pairCode.length === 0) {
      setCodeError('페어링 코드를 입력해 주세요.')
      return false
    }
    if (pairCode.length !== 6) {
      setCodeError('6자리 숫자를 입력해 주세요.')
      return false
    }
    return true
  }

  const handleSubmit = async () => {
    if (!validate()) return
    setLoading(true)
    setApiError(null)
    try {
      const res = await pairIotDevice({
        pairCode,
        ...(displayName.trim() && { displayName: displayName.trim() }),
      })
      onSuccess(res.data)
      onOpenChange(false)
    } catch {
      // TODO: UI 확인용 임시 처리 — 실제 API 연동 후 아래 블록 제거하고 setApiError만 남길 것
      onSuccess({
        id: 0,
        deviceId: `mock-${pairCode}`,
        displayName: displayName.trim() || 'HeyGent',
        status: 'ACTIVE',
        lastSeenAt: null,
        createdAt: null,
        updatedAt: null,
      })
      onOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(isOpen) => {
        if (!isOpen) resetForm()
        onOpenChange(isOpen)
      }}
    >
      <DialogContent className="max-w-sm gap-5">
        <div>
          <DialogTitle className="text-base">기기 등록</DialogTitle>
          <DialogDescription className="text-muted-foreground mt-1 text-sm">
            기기 화면에 표시된 6자리 페어링 코드를 입력해 주세요.
          </DialogDescription>
        </div>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-foreground text-sm font-medium">페어링 코드</label>
            <input
              type="text"
              inputMode="numeric"
              placeholder="6자리 숫자"
              value={pairCode}
              onChange={handlePairCodeChange}
              maxLength={6}
              className="border-border bg-background text-foreground placeholder:text-muted-foreground focus:border-foreground/40 w-full rounded-lg border px-3 py-2 text-sm tracking-widest transition-colors outline-none"
            />
            {codeError && <p className="text-destructive text-xs">{codeError}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-foreground text-sm font-medium">
              기기 이름 <span className="text-muted-foreground font-normal">(선택)</span>
            </label>
            <input
              type="text"
              placeholder="HeyGent 1"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value.slice(0, 100))}
              maxLength={100}
              className="border-border bg-background text-foreground placeholder:text-muted-foreground focus:border-foreground/40 w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none"
            />
            <p className="text-muted-foreground text-right text-xs">{displayName.length}/100</p>
          </div>

          {apiError && (
            <p className="text-destructive bg-destructive/5 rounded-lg px-3 py-2 text-xs">
              {apiError}
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            disabled={loading}
            className="border-border text-foreground hover:bg-accent/50 flex-1 rounded-xl border py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="bg-foreground text-background hover:bg-foreground/85 flex-1 rounded-xl py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loading ? '등록 중...' : '등록하기'}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── ActionButton ─────────────────────────────────────────────────────────────
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

// ── config helpers ───────────────────────────────────────────────────────────
function serverStatusConfig(s: ServerStatus) {
  return s === 'ok'
    ? { label: '정상', color: 'emerald' as const }
    : { label: '오류', color: 'red' as const }
}

function agentStatusConfig(s: AgentStatus) {
  return s === 'idle'
    ? { label: '대기 중', color: 'muted' as const, pulse: false }
    : { label: '작업 중', color: 'blue' as const, pulse: true }
}

// ── DashboardPage ─────────────────────────────────────────────────────────────
export function DashboardPage() {
  const navigate = useNavigate()
  const { setSidebarCollapsed, setSettingsOpen } = useUIStore()

  const [iotDevices, setIotDevices] = useState<IotDevice[]>([])
  const [iotLoading, setIotLoading] = useState(true)
  const [pairingOpen, setPairingOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDeviceId, setPendingDeviceId] = useState<string | null>(null)
  const [newSessionOpen, setNewSessionOpen] = useState(false)

  const fetchDevices = useCallback(
    () =>
      getIotDevices()
        .then((res) => setIotDevices(res.data))
        .catch(() => setIotDevices([]))
        .finally(() => setIotLoading(false)),
    [],
  )

  useEffect(() => {
    void fetchDevices()
  }, [fetchDevices])

  const handleDeregisterRequest = (deviceId: string) => {
    setPendingDeviceId(deviceId)
    setConfirmOpen(true)
  }

  const handleDeregisterConfirm = async () => {
    if (!pendingDeviceId) return
    try {
      await deleteIotDevice(pendingDeviceId)
    } catch {
      // TODO: UI 확인용 임시 처리 — 실제 API 연동 후 제거할 것
    }
    setConfirmOpen(false)
    setPendingDeviceId(null)
    setIotLoading(true)
    await fetchDevices()
  }

  const server = serverStatusConfig(MOCK_SERVER)
  const agent = agentStatusConfig(MOCK_AGENT)
  const device = iotDevices[0] ?? null

  return (
    <div className="bg-background flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-8 px-6 py-10">
        {/* 섹션: 시스템 상태 */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            시스템 상태
          </p>
          <div className="grid grid-cols-2 gap-3">
            <StatusCard
              icon={<Server className="h-4 w-4" />}
              title="서버 연결"
              statusLabel={server.label}
              dotColor={server.color}
            />
            <StatusCard
              icon={<Bot className="h-4 w-4" />}
              title="에이전트"
              statusLabel={agent.label}
              dotColor={agent.color}
              pulse={agent.pulse}
            />
            <div className="col-span-2">
              <IotCard
                loading={iotLoading}
                device={device}
                onRegister={() => setPairingOpen(true)}
                onDeregister={handleDeregisterRequest}
              />
            </div>
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
              label="에이전트 상태 보기"
              onClick={() => navigate('/agent-status')}
            />
            <ActionButton
              icon={<Plus className="h-4 w-4" />}
              label="새 작업 요청하기"
              onClick={() => setNewSessionOpen(true)}
            />
            <ActionButton
              icon={<KeyRound className="h-4 w-4" />}
              label="API 키 등록"
              onClick={() => setSettingsOpen(true, 'apiKeys')}
            />
          </div>
        </motion.section>

        {/* 구분선 */}
        <div className="border-border border-t" />

        {/* 섹션: 최근 상태 로그 */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <p className="text-muted-foreground mb-3 text-xs font-medium tracking-wide uppercase">
            최근 활동
          </p>
          <div className="border-border bg-card divide-border divide-y rounded-xl border">
            {[
              { message: '디바이스가 연결되었습니다.', dot: 'emerald', time: '방금 전' },
              { message: '서버와의 연결이 정상입니다.', dot: 'emerald', time: '1분 전' },
              { message: '에이전트가 대기 상태입니다.', dot: 'muted', time: '2분 전' },
            ].map((log, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-2.5">
                  <StatusDot color={log.dot as 'emerald' | 'muted'} />
                  <span className="text-foreground text-sm">{log.message}</span>
                </div>
                <span className="text-muted-foreground shrink-0 text-xs">{log.time}</span>
              </div>
            ))}
          </div>
        </motion.section>
      </div>

      <PairingModal
        open={pairingOpen}
        onOpenChange={setPairingOpen}
        onSuccess={(registered) => {
          setIotDevices([registered])
          setPairingOpen(false)
        }}
      />

      <DeregisterConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={handleDeregisterConfirm}
      />

      <NewSessionModal
        open={newSessionOpen}
        onOpenChange={setNewSessionOpen}
        onConfirm={(config) => {
          storePendingSessionConfig(config)
          setNewSessionOpen(false)
          if (config && !config.seedDefaultAgents) {
            setSidebarCollapsed(false)
            navigate('/agent-status')
          } else {
            setSidebarCollapsed(true)
            navigate('/new-chat')
          }
        }}
      />
    </div>
  )
}

function storePendingSessionConfig(config: CustomAgentConfig | undefined) {
  if (config === undefined) {
    sessionStorage.removeItem('ai-new-session-config')
    return
  }
  sessionStorage.setItem('ai-new-session-config', JSON.stringify(config))
}
