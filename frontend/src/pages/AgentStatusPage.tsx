import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Code,
  Calendar,
  Apple,
  Activity,
  CheckCircle2,
  Bot,
  Zap,
  Radio,
  Send,
  Sparkles,
  MessageSquare,
  X,
} from 'lucide-react'
import { sessions, agentMeta } from '@/data/sessions'
import type { Message, AgentKey } from '@/data/sessions'
import { useSessionStore } from '@/store/useSessionStore'

const agents = [
  {
    id: 'code-review',
    name: '코드 리뷰 에이전트',
    shortName: 'Code Review',
    status: 'idle' as const,
    description: 'PR을 분석하고 버그, 보안 취약점 및 코드 품질 문제를 식별합니다.',
    icon: Code,
    color: '#3b82f6',
    mapPos: { x: 24, y: 30 },
    currentTask: null as string | null,
  },
  {
    id: 'scheduler',
    name: '스케줄러 / 알림 에이전트',
    shortName: 'Scheduler',
    status: 'running' as const,
    description: '스마트 알림 생성, 일정 관리 및 시기적절한 알림을 전송합니다.',
    icon: Calendar,
    color: '#8b5cf6',
    mapPos: { x: 72, y: 26 },
    currentTask: '오후 5시 회의 준비 알림' as string | null,
  },
  {
    id: 'wellness',
    name: '식단 & 웰니스 에이전트',
    shortName: 'Wellness',
    status: 'ready' as const,
    description: '개인 맞춤형 식사 추천, 영양 추적 및 웰니스 인사이트를 제공합니다.',
    icon: Apple,
    color: '#10b981',
    mapPos: { x: 26, y: 70 },
    currentTask: null as string | null,
  },
  {
    id: 'health',
    name: '건강 데이터 컴패니언',
    shortName: 'Health',
    status: 'idle' as const,
    description: 'IoT 건강 기기를 모니터링하고 센서 데이터를 해석하며 웰니스 지표를 추적합니다.',
    icon: Activity,
    color: '#f59e0b',
    mapPos: { x: 72, y: 68 },
    currentTask: null as string | null,
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

function MessageCard({ content }: { content: string }) {
  return (
    <pre className="bg-muted/60 border-border text-foreground/80 mt-2 overflow-x-auto rounded-xl border px-3 py-2.5 font-mono text-xs leading-relaxed whitespace-pre-wrap">
      {content}
    </pre>
  )
}

function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const meta = msg.agent ? agentMeta[msg.agent as AgentKey] : null
  const AgentIcon = meta?.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {!isUser && (
        <div
          className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
          style={{ backgroundColor: meta ? `${meta.color}18` : '#f1f5f9' }}
        >
          {AgentIcon ? (
            <AgentIcon style={{ color: meta!.color, width: '13px', height: '13px' }} />
          ) : (
            <Bot className="text-primary h-3.5 w-3.5" />
          )}
        </div>
      )}

      <div className={`flex max-w-[85%] flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        {!isUser && meta && (
          <span className="px-1 text-xs font-semibold" style={{ color: meta.color }}>
            {meta.shortName}
          </span>
        )}

        <div
          className={`rounded-2xl px-3 py-2.5 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-primary rounded-tr-sm text-white'
              : 'border-border text-foreground rounded-tl-sm border bg-white'
          }`}
        >
          {msg.text
            .split(/(\*\*[^*]+\*\*)/)
            .map((part, i) =>
              part.startsWith('**') && part.endsWith('**') ? (
                <strong key={i}>{part.slice(2, -2)}</strong>
              ) : (
                <span key={i}>{part}</span>
              ),
            )}
          {msg.card && <MessageCard content={msg.card.content} />}
        </div>

        <div className={`flex items-center gap-1 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <span className="text-muted-foreground text-xs">{msg.time}</span>
          {isUser && <CheckCircle2 className="text-primary/50 h-3 w-3" />}
        </div>
      </div>
    </motion.div>
  )
}

export function AgentStatusPage() {
  const { selectedSessionId, setSelectedSessionId } = useSessionStore()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)

  const activeSessions = sessions.slice(0, 3)
  const currentSessionId = selectedSessionId ?? activeSessions[0]?.id ?? null
  const currentSession = sessions.find((s) => s.id === currentSessionId) ?? activeSessions[0]

  const [messages, setMessages] = useState<Message[]>(() => currentSession?.messages ?? [])
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [syncedSessionId, setSyncedSessionId] = useState(currentSessionId)
  const bottomRef = useRef<HTMLDivElement>(null)

  if (syncedSessionId !== currentSessionId) {
    setSyncedSessionId(currentSessionId)
    setMessages(currentSession?.messages ?? [])
    setInputValue('')
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const agentInfo = currentSession ? agentMeta[currentSession.agentKey] : null
  const AgentIcon = agentInfo?.icon

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || sending || !currentSession) return

    const userMsg: Message = {
      id: `new-${Date.now()}`,
      role: 'user',
      time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
      text,
    }
    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    setSending(true)

    setTimeout(() => {
      const replyMsg: Message = {
        id: `reply-${Date.now()}`,
        role: 'agent',
        agent: currentSession.agentKey,
        time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
        text: '네, 확인했습니다. 추가로 필요한 사항이 있으면 말씀해 주세요.',
      }
      setMessages((prev) => [...prev, replyMsg])
      setSending(false)
    }, 1200)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-background relative flex flex-1 overflow-hidden">
      {/* ── Left: Network Map ─────────────────────────── */}
      <div className="relative flex-1 overflow-hidden">
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
              active={agent.status === 'running' || selectedNodeId === agent.id}
            />
          ))}
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
          const isSelected = selectedNodeId === agent.id
          return (
            <motion.button
              key={agent.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.15 + i * 0.08, type: 'spring', stiffness: 220, damping: 18 }}
              onClick={() => setSelectedNodeId((prev) => (prev === agent.id ? null : agent.id))}
              className="group absolute z-20 -translate-x-1/2 -translate-y-1/2 cursor-pointer"
              style={{ left: `${agent.mapPos.x}%`, top: `${agent.mapPos.y}%` }}
            >
              {agent.status === 'running' && (
                <span
                  className="absolute inset-0 animate-ping rounded-2xl opacity-25"
                  style={{ backgroundColor: agent.color, borderRadius: '18px' }}
                />
              )}
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

        {/* Top-left: label + session selector */}
        <div className="absolute top-5 left-5 z-10 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="border-border flex items-center gap-1.5 rounded-lg border bg-white/90 px-3 py-1.5 shadow-sm backdrop-blur-sm">
              <Radio className="text-primary h-3.5 w-3.5 animate-pulse" />
              <span className="text-foreground text-xs font-semibold">에이전트 네트워크 맵</span>
            </div>
            <div className="border-border rounded-lg border bg-white/90 px-2.5 py-1.5 shadow-sm backdrop-blur-sm">
              <span className="text-muted-foreground text-xs">실시간 시각화</span>
            </div>
          </div>

          {/* Session selector tabs */}
          <div className="flex items-center gap-1.5">
            {activeSessions.map((session) => {
              const meta = agentMeta[session.agentKey]
              const SessionIcon = meta.icon
              const isActive = currentSessionId === session.id
              return (
                <button
                  key={session.id}
                  onClick={() => setSelectedSessionId(session.id)}
                  className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium shadow-sm backdrop-blur-sm transition-all ${
                    isActive
                      ? 'border-primary/30 text-foreground bg-white shadow-md'
                      : 'border-border text-muted-foreground bg-white/80 hover:bg-white'
                  }`}
                >
                  <SessionIcon style={{ color: meta.color, width: '11px', height: '11px' }} />
                  <span className="whitespace-nowrap">{session.title}</span>
                </button>
              )
            })}
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

        {/* Chat toggle button (top-right, visible when panel is closed) */}
        <AnimatePresence>
          {!chatOpen && currentSession && agentInfo && AgentIcon && (
            <motion.button
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.15 }}
              onClick={() => setChatOpen(true)}
              className="border-border absolute top-5 right-5 z-10 flex items-center gap-2 rounded-lg border bg-white/90 px-3 py-1.5 shadow-sm backdrop-blur-sm transition-shadow hover:bg-white hover:shadow-md"
            >
              <AgentIcon style={{ color: agentInfo.color, width: '13px', height: '13px' }} />
              <span className="text-foreground text-xs font-medium">{currentSession.title}</span>
              <MessageSquare className="text-muted-foreground h-3.5 w-3.5" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* ── Right: Sliding Chat Panel (overlay) ──────── */}
      <AnimatePresence>
        {chatOpen && currentSession && agentInfo && AgentIcon && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="border-border absolute top-0 right-0 bottom-0 z-30 flex w-[360px] flex-col overflow-hidden border-l bg-white shadow-2xl"
          >
            {/* Header */}
            <div className="border-border flex flex-shrink-0 items-center gap-3 border-b px-4 py-3">
              <div
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
                style={{ backgroundColor: `${agentInfo.color}18` }}
              >
                <AgentIcon style={{ color: agentInfo.color, width: '15px', height: '15px' }} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-foreground truncate text-sm font-semibold">
                  {currentSession.title}
                </p>
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground text-xs">{currentSession.time}</span>
                  <span className="text-muted-foreground/40 text-xs">·</span>
                  <span className="text-xs font-medium" style={{ color: agentInfo.color }}>
                    {agentInfo.shortName}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setChatOpen(false)}
                className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="bg-border h-px flex-1" />
                <span className="text-muted-foreground flex-shrink-0 px-2 text-xs">
                  {currentSession.time.startsWith('오늘') ? '오늘' : '어제'}
                </span>
                <div className="bg-border h-px flex-1" />
              </div>

              {messages.map((msg) => (
                <ChatMessage key={msg.id} msg={msg} />
              ))}

              <AnimatePresence>
                {sending && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="flex gap-2.5"
                  >
                    <div
                      className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
                      style={{ backgroundColor: `${agentInfo.color}18` }}
                    >
                      <AgentIcon
                        style={{ color: agentInfo.color, width: '13px', height: '13px' }}
                      />
                    </div>
                    <div className="border-border flex items-center gap-1.5 rounded-2xl rounded-tl-sm border bg-white px-3 py-2.5 shadow-sm">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="bg-muted-foreground/50 h-1.5 w-1.5 rounded-full"
                          animate={{ y: [0, -4, 0] }}
                          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                        />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-border flex-shrink-0 border-t bg-white px-4 py-3">
              <div className="bg-background border-border overflow-hidden rounded-xl border shadow-sm transition-shadow hover:shadow-md">
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <Sparkles className="text-primary/50 h-4 w-4 flex-shrink-0" />
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={`${agentInfo.shortName}에게 이어서 질문하기…`}
                    className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!inputValue.trim() || sending}
                    className="bg-primary hover:bg-primary/90 flex-shrink-0 rounded-lg p-1.5 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Send className="h-3.5 w-3.5" />
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
