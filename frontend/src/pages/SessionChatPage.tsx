import { useParams, useLocation, useNavigate } from 'react-router'
import { Send, Mic, Bot, ChevronLeft, AudioLines, Square, X, PhoneOff } from 'lucide-react'
import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { sessions as staticSessions, agentMeta } from '@/data/sessions'
import type { Message, AgentKey } from '@/data/sessions'
import type { CustomAgentConfig } from '@/components/NewSessionModal'
import { useSessionStore } from '@/store/useSessionStore'

// ── 가짜 AI 응답 풀 ──────────────────────────────────────────────
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

// 마이크 웨이브 바 개수
const WAVE_BARS = 5

type ChatMessage = Message & { isNew?: boolean }

interface LocationState {
  firstMessage?: string
  customAgent?: CustomAgentConfig | null
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

// ── 마이크 웨이브 컴포넌트 (입력창 내부용) ──────────────────────
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

// ── 음성대화 오버레이 웨이브 (큰 원형 애니메이션) ─────────────────
type VoiceTurnState = 'user' | 'ai' | 'idle'

function VoiceOrb({ state, volumes }: { state: VoiceTurnState; volumes: number[] }) {
  const avgVol = volumes.reduce((a, b) => a + b, 0) / volumes.length

  if (state === 'user') {
    // 내가 말하는 중 — 볼륨 기반 파동 원
    const scale = 1 + avgVol * 0.6
    return (
      <div className="relative flex h-36 w-36 items-center justify-center">
        {/* 바깥 파동 */}
        <motion.div
          className="absolute rounded-full bg-white/10"
          animate={{ width: 144 * scale, height: 144 * scale }}
          transition={{ duration: 0.08, ease: 'easeOut' }}
        />
        <motion.div
          className="absolute rounded-full bg-white/15"
          animate={{ width: 120 * scale * 0.85, height: 120 * scale * 0.85 }}
          transition={{ duration: 0.08, ease: 'easeOut', delay: 0.02 }}
        />
        {/* 중앙 원 */}
        <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-2xl">
          <Mic className="h-8 w-8 text-gray-800" />
        </div>
      </div>
    )
  }

  if (state === 'ai') {
    // AI가 말하는 중 — 부드러운 pulse 애니메이션
    return (
      <div className="relative flex h-36 w-36 items-center justify-center">
        <motion.div
          className="absolute rounded-full bg-white/10"
          animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0.2, 0.6] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          style={{ width: 144, height: 144 }}
        />
        <motion.div
          className="absolute rounded-full bg-white/20"
          animate={{ scale: [1, 1.18, 1], opacity: [0.8, 0.3, 0.8] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
          style={{ width: 104, height: 104 }}
        />
        <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-2xl">
          <AudioLines className="h-7 w-7 text-gray-800" />
        </div>
      </div>
    )
  }

  // idle — 조용히 대기
  return (
    <div className="relative flex h-36 w-36 items-center justify-center">
      <motion.div
        className="absolute rounded-full bg-white/10"
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
        style={{ width: 144, height: 144 }}
      />
      <div className="relative z-10 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-2xl">
        <Mic className="h-7 w-7 text-gray-400" />
      </div>
    </div>
  )
}

// ── 음성대화 전체화면 오버레이 ────────────────────────────────────
interface VoiceChatOverlayProps {
  agentDisplayName: string
  agentMeta: { color: string; icon: React.ElementType }
  onClose: () => void
}

function VoiceChatOverlay({ agentDisplayName, agentMeta: meta, onClose }: VoiceChatOverlayProps) {
  const [turnState, setTurnState] = useState<VoiceTurnState>('idle')
  const [statusText, setStatusText] = useState('대화를 시작하려면 마이크를 탭하세요')
  const [volumes, setVolumes] = useState<number[]>(Array(WAVE_BARS).fill(0.1))
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const waveRafRef = useRef<number | null>(null)
  const aiTurnRef = useRef<number | null>(null)
  const listenAgainRef = useRef<number | null>(null)

  const stopMicStream = useCallback(() => {
    if (waveRafRef.current) cancelAnimationFrame(waveRafRef.current)
    if (micStreamRef.current) micStreamRef.current.getTracks().forEach((t) => t.stop())
    if (audioContextRef.current) audioContextRef.current.close()
    audioContextRef.current = null
    analyserRef.current = null
    micStreamRef.current = null
    setVolumes(Array(WAVE_BARS).fill(0.1))
  }, [])

  const startListeningRef = useRef<() => void>(() => {})

  const startListening = useCallback(async () => {
    setTurnState('user')
    setStatusText('듣고 있어요...')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const ctx = new AudioContext()
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      audioContextRef.current = ctx
      analyserRef.current = analyser
      micStreamRef.current = stream

      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        const step = Math.floor(data.length / WAVE_BARS)
        const vols = Array.from({ length: WAVE_BARS }, (_, i) => {
          const slice = data.slice(i * step, (i + 1) * step)
          const avg = slice.reduce((a, b) => a + b, 0) / slice.length
          return Math.min(1, avg / 180)
        })
        setVolumes(vols)
        waveRafRef.current = requestAnimationFrame(tick)
      }
      waveRafRef.current = requestAnimationFrame(tick)
    } catch {
      const fake = () => {
        setVolumes(Array.from({ length: WAVE_BARS }, () => 0.15 + Math.random() * 0.65))
        waveRafRef.current = requestAnimationFrame(fake)
      }
      waveRafRef.current = requestAnimationFrame(fake)
    }

    // 3초 후 자동으로 AI 턴으로 전환 (시뮬레이션)
    aiTurnRef.current = window.setTimeout(
      () => {
        stopMicStream()
        setTurnState('ai')
        setStatusText(`${agentDisplayName}이(가) 응답하는 중...`)
        const replyDelay = 2000 + Math.random() * 2000
        listenAgainRef.current = window.setTimeout(() => {
          startListeningRef.current()
        }, replyDelay)
      },
      3000 + Math.random() * 2000,
    )
  }, [agentDisplayName, stopMicStream])

  useEffect(() => {
    startListeningRef.current = startListening
  }, [startListening])

  const handleMicTap = () => {
    if (turnState === 'idle') {
      startListening()
    } else if (turnState === 'user') {
      if (aiTurnRef.current) clearTimeout(aiTurnRef.current)
      stopMicStream()
      setTurnState('ai')
      setStatusText(`${agentDisplayName}이(가) 응답하는 중...`)
      listenAgainRef.current = window.setTimeout(
        () => {
          startListeningRef.current()
        },
        2000 + Math.random() * 2000,
      )
    } else if (turnState === 'ai') {
      if (listenAgainRef.current) clearTimeout(listenAgainRef.current)
      startListening()
    }
  }

  const handleClose = useCallback(() => {
    if (aiTurnRef.current) clearTimeout(aiTurnRef.current)
    if (listenAgainRef.current) clearTimeout(listenAgainRef.current)
    stopMicStream()
    onClose()
  }, [onClose, stopMicStream])

  useEffect(
    () => () => {
      if (aiTurnRef.current) clearTimeout(aiTurnRef.current)
      if (listenAgainRef.current) clearTimeout(listenAgainRef.current)
      stopMicStream()
    },
    [stopMicStream],
  )

  const turnLabel =
    turnState === 'user'
      ? '말하는 중'
      : turnState === 'ai'
        ? `${agentDisplayName} 응답 중`
        : '대기 중'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-between overflow-hidden"
      style={{
        background: 'linear-gradient(160deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%)',
      }}
    >
      {/* 상단 닫기 */}
      <div className="flex w-full items-center justify-between px-6 pt-6">
        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${meta.color}30` }}
          >
            <meta.icon style={{ color: meta.color, width: 14, height: 14 }} />
          </div>
          <span className="text-sm font-medium text-white/80">{agentDisplayName}</span>
        </div>
        <button
          onClick={handleClose}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-white/60 transition-colors hover:bg-white/20 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* 중앙 오브 + 상태 */}
      <div className="flex flex-col items-center gap-8">
        <VoiceOrb state={turnState} volumes={volumes} />

        <div className="flex flex-col items-center gap-2 text-center">
          <motion.div
            key={turnLabel}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-1.5"
          >
            {turnState !== 'idle' && (
              <motion.span
                className="inline-block h-1.5 w-1.5 rounded-full bg-green-400"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              />
            )}
            <span className="text-sm font-medium text-white/70">{turnLabel}</span>
          </motion.div>
          <motion.p
            key={statusText}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="text-xs text-white/40"
          >
            {statusText}
          </motion.p>
        </div>
      </div>

      {/* 하단 컨트롤 */}
      <div className="mb-12 flex flex-col items-center gap-6">
        {/* 마이크 탭 버튼 */}
        <button
          onClick={handleMicTap}
          className={`flex h-16 w-16 items-center justify-center rounded-full shadow-lg transition-all duration-200 active:scale-95 ${
            turnState === 'user' ? 'bg-white shadow-white/20' : 'bg-white/15 hover:bg-white/25'
          }`}
        >
          {turnState === 'user' ? (
            <Square className="h-5 w-5 fill-gray-800 text-gray-800" />
          ) : (
            <Mic className={`h-6 w-6 ${turnState === 'ai' ? 'text-white/40' : 'text-white'}`} />
          )}
        </button>
        <p className="text-xs text-white/30">
          {turnState === 'user'
            ? '탭하면 전송'
            : turnState === 'ai'
              ? '탭하면 끊기'
              : '탭하면 시작'}
        </p>

        {/* 통화 종료 버튼 */}
        <button
          onClick={handleClose}
          className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500 shadow-lg shadow-red-500/30 transition-all duration-200 hover:bg-red-600 active:scale-95"
        >
          <PhoneOff className="h-5 w-5 text-white" />
        </button>
      </div>
    </motion.div>
  )
}

export function SessionChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const locationState = location.state as LocationState | null
  const { addDynamicSession, dynamicSessions } = useSessionStore()

  // 기존 세션: static + dynamic 모두에서 탐색
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
  const [voiceChatOpen, setVoiceChatOpen] = useState(false)

  // 마이크
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

  // ── 마이크 웨이브 루프 ──────────────────────────────────────────
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
    if (micStreamRef.current) micStreamRef.current.getTracks().forEach((t) => t.stop())
    if (audioContextRef.current) audioContextRef.current.close()
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
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      audioContextRef.current = ctx
      analyserRef.current = analyser
      micStreamRef.current = stream
      setIsRecording(true)
      startWaveLoop(analyser)
    } catch {
      // 마이크 권한 거부 시 단순 토글만
      setIsRecording(true)
      // 가짜 웨이브 애니메이션
      const fake = () => {
        setWaveVolumes(Array.from({ length: WAVE_BARS }, () => 0.1 + Math.random() * 0.8))
        waveRafRef.current = requestAnimationFrame(fake)
      }
      waveRafRef.current = requestAnimationFrame(fake)
    }
  }, [isRecording, startWaveLoop, stopWave])

  // 언마운트 시 정리
  useEffect(
    () => () => {
      stopWave()
    },
    [stopWave],
  )

  // ── 스크롤 ──────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // ── 세션 등록 (최초 메시지 전송 시) ───────────────────────────────
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

  // ── 메시지 전송 ─────────────────────────────────────────────────
  const sendMessage = useCallback(
    (text: string) => {
      registerSession(text)
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        text,
        time: nowTime(),
        isNew: true,
      }
      setMessages((prev) => [...prev, userMsg])

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
        const agentMsg: ChatMessage = {
          id: `a-${Date.now()}`,
          role: 'agent',
          agent: existingSession?.agentKey ?? ('main' as AgentKey),
          text: randomReply(),
          time: nowTime(),
          isNew: true,
        }
        setMessages((prev) => [...prev, agentMsg])
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

  // ── 첫 메시지 자동 전송 ─────────────────────────────────────────
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
    // 마이크 녹음 중이면 중지
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
      {/* 음성대화 오버레이 */}
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

        {/* 로딩 버블 */}
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
      <div className="border-border shrink-0 border-t px-4 py-3">
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
            disabled={isTyping}
            className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent text-sm outline-none disabled:opacity-60"
          />

          {/* 마이크 버튼 */}
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

          {isTyping ? (
            <button
              onClick={handleStop}
              title="응답 중지"
              className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-lg p-1.5 text-white transition-colors"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </button>
          ) : inputValue.trim() ? (
            <button
              onClick={handleSend}
              title="전송"
              className="bg-primary hover:bg-primary/90 shrink-0 rounded-lg p-1.5 text-white transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={() => setVoiceChatOpen(true)}
              title="음성 대화 모드"
              className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-lg p-1.5 text-white transition-colors"
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
            isUser ? 'bg-primary text-white' : 'border-border border bg-white'
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
