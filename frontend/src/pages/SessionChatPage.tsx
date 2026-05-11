import { useParams, useLocation, useNavigate } from 'react-router'
import { Send, Mic, Bot, ChevronLeft, AudioLines, Square, X, PhoneOff } from 'lucide-react'
import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence, useMotionValue, useSpring } from 'motion/react'
import { sessions as staticSessions, agentMeta } from '@/data/sessions'
import type { Message, AgentKey } from '@/data/sessions'
import type { CustomAgentConfig } from '@/components/session/NewSessionModal'
import { useSessionStore } from '@/store/useSessionStore'

const FAKE_REPLIES = [
  '네, 말씀하신 내용 잘 이해했습니다. 바로 처리해 드릴게요.',
  '좋은 질문이에요! 분석해보니 몇 가지 방법이 있는데, 가장 효율적인 방법을 추천드릴게요.',
  '알겠습니다. 관련 데이터를 확인해보겠습니다. 잠시 기다려 주세요.',
  '해당 내용을 검토했습니다. 제가 도와드릴 수 있는 최선의 방법을 안내해 드릴게요.',
  '좋아요! 이 부분은 제가 잘 알고 있어요. 단계별로 설명해 드릴게요.',
  '흥미로운 요청이네요. 다양한 관점에서 살펴보고 답변 드릴게요.',
  '확인했습니다. 현재 상태를 분석해서 최적의 방안을 찾아볼게요.',
]

const LOADING_STEPS = [
  '요청을 분석하는 중...',
  '관련 정보를 검색하는 중...',
  '응답을 생성하는 중...',
]

const WAVE_BARS = 5

type ChatMessage = Message & { isNew?: boolean }

interface LocationState {
  firstMessage?: string
  customAgent?: CustomAgentConfig | null
  voiceMode?: boolean
}

function nowTime() {
  const d = new Date()
  const h = d.getHours()
  const m = String(d.getMinutes()).padStart(2, '0')
  const period = h >= 12 ? '오후' : '오전'
  return `${period} ${h > 12 ? h - 12 : h}:${m}`
}

function nowTimeShort() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

function randomReply() {
  return FAKE_REPLIES[Math.floor(Math.random() * FAKE_REPLIES.length)]
}

// ── 입력창 마이크 웨이브 (작은 바) ───────────────────────────────
function VoiceWave({ volumes }: { volumes: number[] }) {
  return (
    <div className="flex items-center gap-0.75">
      {volumes.map((vol, i) => (
        <motion.div
          key={i}
          className="w-0.75 rounded-full bg-white"
          animate={{ height: Math.max(4, vol * 24) }}
          transition={{ duration: 0.08, ease: 'easeOut' }}
        />
      ))}
    </div>
  )
}

// ── 음성대화 오버레이 ─────────────────────────────────────────────
type VoiceTurnState = 'user' | 'ai' | 'idle'

// 볼륨 기반 spring 원 (user 말하는 중)
function UserOrb({ avgVolume }: { avgVolume: number }) {
  const scale = useMotionValue(1)
  const springScale = useSpring(scale, { stiffness: 200, damping: 20 })

  useEffect(() => {
    scale.set(1 + avgVolume * 0.7)
  }, [avgVolume, scale])

  return (
    <div className="relative flex h-40 w-40 items-center justify-center">
      <motion.div
        className="absolute rounded-full bg-white/8"
        style={{ width: 160, height: 160, scaleX: springScale, scaleY: springScale }}
      />
      <motion.div
        className="absolute rounded-full bg-white/12"
        style={{ width: 128, height: 128, scaleX: springScale, scaleY: springScale }}
      />
      <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-2xl">
        <Mic className="h-8 w-8 text-gray-800" />
      </div>
    </div>
  )
}

// AI 말하는 중 pulse 원
function AiOrb() {
  return (
    <div className="relative flex h-40 w-40 items-center justify-center">
      <motion.div
        className="absolute rounded-full bg-white/8"
        style={{ width: 160, height: 160 }}
        animate={{ scale: [1, 1.28, 1], opacity: [0.7, 0.2, 0.7] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute rounded-full bg-white/15"
        style={{ width: 112, height: 112 }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.9, 0.3, 0.9] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut', delay: 0.35 }}
      />
      <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-2xl">
        <AudioLines className="h-7 w-7 text-gray-800" />
      </div>
    </div>
  )
}

// 대기 중 idle 원
function IdleOrb() {
  return (
    <div className="relative flex h-40 w-40 items-center justify-center">
      <motion.div
        className="absolute rounded-full bg-white/8"
        style={{ width: 160, height: 160 }}
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
      />
      <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white/20 shadow-xl">
        <Mic className="h-7 w-7 text-white/60" />
      </div>
    </div>
  )
}

interface VoiceChatOverlayProps {
  agentDisplayName: string
  agentMeta: { color: string; icon: React.ElementType }
  onClose: () => void
}

function VoiceChatOverlay({ agentDisplayName, agentMeta: meta, onClose }: VoiceChatOverlayProps) {
  const [turnState, setTurnState] = useState<VoiceTurnState>('idle')
  const [statusText, setStatusText] = useState('탭해서 대화 시작')
  const [avgVolume, setAvgVolume] = useState(0)

  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const rafRef = useRef<number | null>(null)
  const aiTimerRef = useRef<number | null>(null)
  const nextListenRef = useRef<number | null>(null)
  const startListeningRef = useRef<(() => Promise<void>) | null>(null)

  const stopMic = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    micStreamRef.current?.getTracks().forEach((t) => t.stop())
    audioCtxRef.current?.close()
    audioCtxRef.current = null
    analyserRef.current = null
    micStreamRef.current = null
    setAvgVolume(0)
  }, [])

  const startListening = useCallback(async () => {
    setTurnState('user')
    setStatusText('듣고 있어요...')

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const ctx = new AudioContext()
      const src = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      src.connect(analyser)
      audioCtxRef.current = ctx
      analyserRef.current = analyser
      micStreamRef.current = stream

      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        const avg = data.reduce((a, b) => a + b, 0) / data.length / 255
        setAvgVolume(avg)
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    } catch {
      // 마이크 권한 없을 때 가짜 볼륨
      const fake = () => {
        setAvgVolume(0.1 + Math.random() * 0.5)
        rafRef.current = requestAnimationFrame(fake)
      }
      rafRef.current = requestAnimationFrame(fake)
    }

    // 3~5초 후 AI 턴
    aiTimerRef.current = window.setTimeout(
      () => {
        stopMic()
        setTurnState('ai')
        setStatusText(`${agentDisplayName}이(가) 응답하는 중...`)
        nextListenRef.current = window.setTimeout(
          () => {
            startListeningRef.current?.()
          },
          2000 + Math.random() * 2000,
        )
      },
      3000 + Math.random() * 2000,
    )
  }, [agentDisplayName, stopMic])

  useEffect(() => {
    startListeningRef.current = startListening
  }, [startListening])

  const clearTimers = useCallback(() => {
    if (aiTimerRef.current) clearTimeout(aiTimerRef.current)
    if (nextListenRef.current) clearTimeout(nextListenRef.current)
    aiTimerRef.current = null
    nextListenRef.current = null
  }, [])

  const handleMicTap = () => {
    if (turnState === 'idle') {
      startListening()
    } else if (turnState === 'user') {
      clearTimers()
      stopMic()
      setTurnState('ai')
      setStatusText(`${agentDisplayName}이(가) 응답하는 중...`)
      nextListenRef.current = window.setTimeout(
        () => {
          startListeningRef.current?.()
        },
        2000 + Math.random() * 2000,
      )
    } else {
      clearTimers()
      startListening()
    }
  }

  const handleClose = useCallback(() => {
    clearTimers()
    stopMic()
    onClose()
  }, [clearTimers, onClose, stopMic])

  useEffect(
    () => () => {
      clearTimers()
      stopMic()
    },
    [clearTimers, stopMic],
  )

  const turnLabel =
    turnState === 'user'
      ? '내가 말하는 중'
      : turnState === 'ai'
        ? `${agentDisplayName} 응답 중`
        : '대기 중'

  const micHint =
    turnState === 'user'
      ? '탭하면 AI에게 넘기기'
      : turnState === 'ai'
        ? '탭하면 끊기'
        : '탭하면 시작'

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.22 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-between"
      style={{ background: 'linear-gradient(160deg, #0f0f1a 0%, #151526 45%, #0d1f3c 100%)' }}
    >
      {/* 상단 */}
      <div className="flex w-full items-center justify-between px-6 pt-8">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-xl"
            style={{ backgroundColor: `${meta.color}25` }}
          >
            <meta.icon style={{ color: meta.color, width: 15, height: 15 }} />
          </div>
          <div>
            <p className="text-sm font-semibold text-white/90">{agentDisplayName}</p>
            <AnimatePresence mode="wait">
              <motion.p
                key={turnLabel}
                initial={{ opacity: 0, y: 3 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -3 }}
                transition={{ duration: 0.18 }}
                className="text-xs text-white/40"
              >
                {turnLabel}
              </motion.p>
            </AnimatePresence>
          </div>
        </div>
        <button
          onClick={handleClose}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white/50 transition-colors hover:bg-white/20 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* 중앙 Orb */}
      <div className="flex flex-col items-center gap-10">
        <AnimatePresence mode="wait">
          {turnState === 'user' && (
            <motion.div
              key="user-orb"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.22 }}
            >
              <UserOrb avgVolume={avgVolume} />
            </motion.div>
          )}
          {turnState === 'ai' && (
            <motion.div
              key="ai-orb"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.22 }}
            >
              <AiOrb />
            </motion.div>
          )}
          {turnState === 'idle' && (
            <motion.div
              key="idle-orb"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.22 }}
            >
              <IdleOrb />
            </motion.div>
          )}
        </AnimatePresence>

        {/* 상태 텍스트 */}
        <AnimatePresence mode="wait">
          <motion.p
            key={statusText}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="text-sm text-white/50"
          >
            {statusText}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* 하단 컨트롤 */}
      <div className="mb-14 flex flex-col items-center gap-8">
        {/* 마이크 / 멈춤 버튼 */}
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleMicTap}
            className={`flex h-16 w-16 items-center justify-center rounded-full shadow-lg transition-all duration-200 active:scale-90 ${
              turnState === 'user'
                ? 'bg-white shadow-white/20'
                : turnState === 'ai'
                  ? 'cursor-default bg-white/10'
                  : 'bg-white/15 hover:bg-white/25'
            }`}
          >
            {turnState === 'user' ? (
              <Square className="h-5 w-5 fill-gray-800 text-gray-800" />
            ) : (
              <Mic className={`h-6 w-6 ${turnState === 'ai' ? 'text-white/25' : 'text-white'}`} />
            )}
          </button>
          <p className="text-xs text-white/25">{micHint}</p>
        </div>

        {/* 종료 버튼 */}
        <button
          onClick={handleClose}
          className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500 shadow-xl shadow-red-500/25 transition-all duration-200 hover:bg-red-600 active:scale-90"
        >
          <PhoneOff className="h-6 w-6 text-white" />
        </button>
      </div>
    </motion.div>
  )
}

// ─────────────────────────────────────────────────────────────────
export function SessionChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const locationState = location.state as LocationState | null
  const { addDynamicSession, dynamicSessions } = useSessionStore()

  const existingSession = sessionId
    ? (dynamicSessions.find((s) => s.id === sessionId) ??
      staticSessions.find((s) => s.id === sessionId))
    : null

  const customAgent = locationState?.customAgent ?? null
  const sessionRegistered = useRef(false)

  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    existingSession ? existingSession.messages : [],
  )
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [voiceChatOpen, setVoiceChatOpen] = useState(() => !!locationState?.voiceMode)

  // 입력창 마이크 (텍스트 보조용 음성 입력)
  const [isRecording, setIsRecording] = useState(false)
  const [waveVolumes, setWaveVolumes] = useState<number[]>(Array(WAVE_BARS).fill(0.15))
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const waveRafRef = useRef<number | null>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const hasInitialized = useRef(false)
  const replyTimeoutRef = useRef<number | null>(null)
  const stepIntervalRef = useRef<number | null>(null)

  const startWaveLoop = useCallback((analyser: AnalyserNode) => {
    const data = new Uint8Array(analyser.frequencyBinCount)
    const tick = () => {
      analyser.getByteFrequencyData(data)
      const step = Math.floor(data.length / WAVE_BARS)
      const vols = Array.from({ length: WAVE_BARS }, (_, i) => {
        const slice = data.slice(i * step, (i + 1) * step)
        const avg = slice.reduce((a, b) => a + b, 0) / slice.length
        return Math.min(1, avg / 200)
      })
      setWaveVolumes(vols)
      waveRafRef.current = requestAnimationFrame(tick)
    }
    waveRafRef.current = requestAnimationFrame(tick)
  }, [])

  const stopWave = useCallback(() => {
    if (waveRafRef.current) cancelAnimationFrame(waveRafRef.current)
    micStreamRef.current?.getTracks().forEach((t) => t.stop())
    audioContextRef.current?.close()
    audioContextRef.current = null
    analyserRef.current = null
    micStreamRef.current = null
    setWaveVolumes(Array(WAVE_BARS).fill(0.15))
  }, [])

  const handleMicToggle = useCallback(async () => {
    if (isRecording) {
      stopWave()
      setIsRecording(false)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const ctx = new AudioContext()
      const src = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      src.connect(analyser)
      audioContextRef.current = ctx
      analyserRef.current = analyser
      micStreamRef.current = stream
      setIsRecording(true)
      startWaveLoop(analyser)
    } catch {
      setIsRecording(true)
      const fake = () => {
        setWaveVolumes(Array.from({ length: WAVE_BARS }, () => 0.1 + Math.random() * 0.8))
        waveRafRef.current = requestAnimationFrame(fake)
      }
      waveRafRef.current = requestAnimationFrame(fake)
    }
  }, [isRecording, startWaveLoop, stopWave])

  useEffect(
    () => () => {
      stopWave()
    },
    [stopWave],
  )

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const registerSession = useCallback(
    (firstText: string) => {
      if (sessionRegistered.current || existingSession) return
      sessionRegistered.current = true
      const id = `dyn-${Date.now()}`
      const title = customAgent?.agentName ? `${customAgent.agentName}와의 대화` : 'Heygent'
      addDynamicSession({
        id,
        title,
        time: nowTimeShort(),
        preview: firstText.slice(0, 30),
        agentKey: 'main',
        messages: [],
      })
    },
    [existingSession, customAgent, addDynamicSession],
  )

  const sendMessage = useCallback(
    (text: string) => {
      registerSession(text)
      setMessages((prev) => [
        ...prev,
        { id: `u-${Date.now()}`, role: 'user', text, time: nowTime(), isNew: true },
      ])
      setIsTyping(true)
      setLoadingStep(0)
      stepIntervalRef.current = window.setInterval(() => {
        setLoadingStep((s) => (s + 1) % LOADING_STEPS.length)
      }, 700)
      const delay = 1000 + Math.random() * 2000
      replyTimeoutRef.current = window.setTimeout(() => {
        if (stepIntervalRef.current) clearInterval(stepIntervalRef.current)
        stepIntervalRef.current = null
        replyTimeoutRef.current = null
        setIsTyping(false)
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: 'agent',
            agent: existingSession?.agentKey ?? ('main' as AgentKey),
            text: randomReply(),
            time: nowTime(),
            isNew: true,
          },
        ])
      }, delay)
    },
    [existingSession, registerSession],
  )

  const handleStop = useCallback(() => {
    if (replyTimeoutRef.current) clearTimeout(replyTimeoutRef.current)
    if (stepIntervalRef.current) clearInterval(stepIntervalRef.current)
    replyTimeoutRef.current = null
    stepIntervalRef.current = null
    setIsTyping(false)
  }, [])

  useEffect(() => {
    if (!existingSession && locationState?.firstMessage && !hasInitialized.current) {
      hasInitialized.current = true
      sendMessage(locationState.firstMessage)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || isTyping) return
    setInputValue('')
    if (isRecording) {
      stopWave()
      setIsRecording(false)
    }
    sendMessage(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
  }

  const meta = existingSession ? agentMeta[existingSession.agentKey] : agentMeta['main']
  const agentDisplayName = customAgent?.agentName || meta.shortName
  const title =
    existingSession?.title ??
    (customAgent?.agentName ? `${customAgent.agentName}와의 대화` : 'Heygent')

  return (
    <div className="bg-background relative flex flex-1 flex-col overflow-hidden">
      <AnimatePresence>
        {voiceChatOpen && (
          <VoiceChatOverlay
            agentDisplayName={agentDisplayName}
            agentMeta={meta}
            onClose={() => setVoiceChatOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="border-border flex h-12 shrink-0 items-center gap-3 border-b px-4">
        <button
          onClick={() => navigate(-1)}
          className="text-muted-foreground hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-md transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div
          className="flex h-6 w-6 items-center justify-center rounded-md"
          style={{ backgroundColor: `${meta.color}20` }}
        >
          <meta.icon style={{ color: meta.color, width: 14, height: 14 }} />
        </div>
        <span className="text-foreground text-sm font-semibold">{title}</span>
        {existingSession && (
          <span className="text-muted-foreground text-xs">{existingSession.time}</span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            agentKey={existingSession?.agentKey}
            agentDisplayName={agentDisplayName}
          />
        ))}

        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.2 }}
              className="flex gap-3"
            >
              <div
                className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
                style={{ backgroundColor: `${meta.color}20` }}
              >
                <meta.icon style={{ color: meta.color, width: 14, height: 14 }} />
              </div>
              <div className="flex flex-col gap-1.5">
                <span className="text-muted-foreground px-1 text-xs">{agentDisplayName}</span>
                <div className="border-border flex items-center gap-2.5 rounded-2xl border bg-white px-4 py-2.5">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.span
                        key={i}
                        className="bg-muted-foreground/50 h-1.5 w-1.5 rounded-full"
                        animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
                        transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
                      />
                    ))}
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={loadingStep}
                      initial={{ opacity: 0, x: 4 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -4 }}
                      transition={{ duration: 0.2 }}
                      className="text-muted-foreground text-xs"
                    >
                      {LOADING_STEPS[loadingStep]}
                    </motion.span>
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 py-3">
        <div className="border-border flex items-center gap-3 overflow-hidden rounded-xl border bg-white px-4 py-2.5 shadow-sm">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isTyping
                ? '응답을 기다리는 중...'
                : isRecording
                  ? '음성 입력 중...'
                  : '메시지를 입력하세요...'
            }
            className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none"
          />

          {/* 입력 보조 마이크 버튼 */}
          <button
            onClick={handleMicToggle}
            disabled={isTyping}
            className={`relative flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2 transition-all duration-200 disabled:opacity-40 ${
              isRecording
                ? 'bg-red-500 text-white shadow-md shadow-red-200'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {isRecording ? <VoiceWave volumes={waveVolumes} /> : <Mic className="h-4 w-4" />}
          </button>

          {/* 오른쪽 버튼: 중지 / 전송 / 음성대화 */}
          {isTyping ? (
            <button
              onClick={handleStop}
              title="응답 중지"
              className="bg-foreground text-background hover:bg-foreground/85 p-1.5_TBR shrink-0 rounded-lg transition-colors"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </button>
          ) : inputValue.trim() ? (
            <button
              onClick={handleSend}
              title="전송"
              className="bg-primary text-primary-foreground hover:bg-primary/90 shrink-0 rounded-lg p-1.5 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={() => setVoiceChatOpen(true)}
              title="음성 대화 모드"
              className="bg-foreground text-background hover:bg-foreground/85 p-1.5_TBR shrink-0 rounded-lg transition-colors"
            >
              <AudioLines className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── 메시지 버블 ───────────────────────────────────────────────────
function MessageBubble({
  msg,
  agentKey,
  agentDisplayName,
}: {
  msg: ChatMessage
  agentKey?: string
  agentDisplayName?: string
}) {
  const isUser = msg.role === 'user'
  const meta = msg.agent ? agentMeta[msg.agent] : agentKey ? agentMeta[agentKey as AgentKey] : null
  const displayName = agentDisplayName || meta?.shortName || ''

  return (
    <motion.div
      initial={msg.isNew ? { opacity: 0, y: 10 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {!isUser && (
        <div
          className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full"
          style={{ backgroundColor: meta ? `${meta.color}20` : '#f3f4f6' }}
        >
          {meta ? (
            <meta.icon style={{ color: meta.color, width: 14, height: 14 }} />
          ) : (
            <Bot className="h-3.5 w-3.5 text-gray-500" />
          )}
        </div>
      )}

      <div className={`flex max-w-[72%] flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'}`}>
        <span className="text-muted-foreground px-1 text-xs">
          {!isUser ? `${displayName} · ` : ''}
          {msg.time}
        </span>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser ? 'bg-primary text-primary-foreground' : 'border-border bg-card border'
          }`}
        >
          {msg.text.split('\n').map((line, i) => (
            <p key={i} className={i > 0 ? 'mt-1' : ''}>
              {line || <br />}
            </p>
          ))}
        </div>
        {msg.card && (
          <div className="border-border w-full rounded-xl border bg-gray-50 px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre-wrap text-gray-700">
            {msg.card.content}
          </div>
        )}
      </div>
    </motion.div>
  )
}
