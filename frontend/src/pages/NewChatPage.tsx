import { Sparkles, Send, Code, Calendar, Apple, Activity, Mic, Bot, AudioLines } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import {
  type AiRealtimeAuthStatus,
  type AiRealtimeConnectionStatus,
  getFramePayload,
  getStringField,
} from '@/realtime/aiRealtimeTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'
import type { CustomAgentConfig } from '@/components/NewSessionModal'

const suggestedPrompts = [
  {
    text: '이 PR 검토해줘',
    icon: Code,
    bg: 'hover:bg-accent hover:border-border hover:text-accent-foreground',
  },
  {
    text: '오후 5시에 알려줘',
    icon: Calendar,
    bg: 'hover:bg-accent hover:border-border hover:text-accent-foreground',
  },
  {
    text: '저녁 메뉴 추천해줘',
    icon: Apple,
    bg: 'hover:bg-accent hover:border-border hover:text-accent-foreground',
  },
  {
    text: '운동 끝나면 알려줘',
    icon: Activity,
    bg: 'hover:bg-accent hover:border-border hover:text-accent-foreground',
  },
]

export function NewChatPage() {
  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const navigate = useNavigate()
  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const accessToken = useAuthStore((state) => state.accessToken)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const providerMessage =
    commandClient === null
      ? getRealtimeUnavailableMessage(connectionStatus, authStatus, realtimeError, accessToken)
      : null
  const providerPending =
    commandClient === null &&
    shouldWaitForRealtime(connectionStatus, authStatus, realtimeError, accessToken)

  const handleVoiceInput = () => {
    setIsRecording(!isRecording)
  }

  const handleSend = async () => {
    const content = inputValue.trim()
    if (!content || isSending) return
    if (commandClient === null) {
      setSendError(
        getRealtimeUnavailableMessage(connectionStatus, authStatus, realtimeError, accessToken),
      )
      return
    }

    setIsSending(true)
    setSendError(null)

    try {
      const pendingConfig = readPendingSessionConfig()
      const acceptedFrame = await sendMessage({
        content,
        settings: pendingConfig?.persona.trim()
          ? { systemPrompt: pendingConfig.persona.trim() }
          : undefined,
        inputPayload:
          pendingConfig === null
            ? undefined
            : {
                sessionConfigSnapshot: {
                  agentName: pendingConfig.agentName,
                  persona: pendingConfig.persona,
                  callName: pendingConfig.callName,
                  profileImageProvided: pendingConfig.profileImage !== null,
                },
              },
      })
      const payload = getFramePayload(acceptedFrame)
      const acceptedSessionId =
        getStringField(payload, 'session_id', 'sessionId') ??
        getStringField(acceptedFrame, 'session_id', 'sessionId')

      if (acceptedSessionId === undefined) {
        throw new Error('accepted 응답에 sessionId가 없습니다.')
      }

      navigate(`/session/${acceptedSessionId}`)
      clearPendingSessionConfig()
    } catch (error) {
      setSendError(error instanceof Error ? error.message : '새 채팅을 시작하지 못했습니다.')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') void handleSend()
  }

  return (
    <div className="bg-background flex flex-1 flex-col items-center justify-center px-8">
      <div className="w-full max-w-2xl space-y-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="space-y-2 text-center"
        >
          <div className="mb-4 flex justify-center">
            <div className="from-primary to-chart-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br shadow-sm">
              <Bot className="h-6 w-6 text-white" />
            </div>
          </div>
          <h1 className="text-foreground text-2xl font-bold">새로운 대화 시작</h1>
          <p className="text-muted-foreground text-sm">
            무엇이든 물어보세요. 적합한 전문 에이전트에게 연결해 드릴게요.
          </p>
        </motion.div>

        {/* Input Area */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.08 }}
        >
          <div className="border-border bg-card overflow-hidden rounded-2xl border shadow-sm transition-shadow duration-200 hover:shadow-md">
            {/* Input row */}
            <div className="flex items-center gap-3 px-5 py-4">
              <Sparkles className="text-primary/60 h-5 w-5 shrink-0" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="무엇이든 물어보세요..."
                className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent outline-none"
                style={{ fontSize: '15px' }}
                autoFocus
              />
              <button
                type="button"
                onClick={handleVoiceInput}
                aria-label={isRecording ? '음성 입력 중지' : '음성 입력 시작'}
                className={`shrink-0 rounded-xl p-2.5 transition-colors ${
                  isRecording
                    ? 'animate-pulse bg-red-500 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                title="음성 입력"
              >
                <Mic className="h-4 w-4" />
              </button>
              {inputValue.trim() ? (
                <button
                  type="button"
                  onClick={() => void handleSend()}
                  aria-label="새 대화 메시지 보내기"
                  className="bg-primary hover:bg-primary/90 shrink-0 rounded-xl p-2 text-white transition-colors disabled:opacity-40"
                  disabled={isSending || commandClient === null}
                >
                  <Send className={`h-4 w-4 ${isSending ? 'animate-pulse' : ''}`} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate('/session/voice', { state: { voiceMode: true } })}
                  aria-label="음성 대화 모드"
                  title="음성 대화 모드"
                  className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-xl p-2 text-white transition-colors"
                >
                  <AudioLines className="h-4 w-4" />
                </button>
              )}
            </div>
            {sendError && <p className="text-destructive px-5 pb-2 text-xs">{sendError}</p>}
            {!sendError && providerMessage && (
              <p
                className={`px-5 pb-2 text-xs ${
                  providerPending ? 'text-muted-foreground' : 'text-destructive'
                }`}
              >
                {providerMessage}
              </p>
            )}

            {/* Divider */}
            <div className="border-border/60 mx-5 border-t" />

            {/* Prompt chips */}
            <div className="flex flex-wrap items-center gap-2 px-5 py-3">
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setInputValue(prompt.text)}
                  aria-label={`추천 프롬프트 선택: ${prompt.text}`}
                  className={`bg-muted text-muted-foreground flex items-center gap-1.5 rounded-lg border border-transparent px-3 py-1.5 transition-all duration-150 ${prompt.bg}`}
                  style={{ fontSize: '13px' }}
                >
                  <prompt.icon className="h-3.5 w-3.5" />
                  <span>{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function isRealtimePending(connectionStatus: AiRealtimeConnectionStatus) {
  return (
    connectionStatus === 'connecting' ||
    connectionStatus === 'open' ||
    connectionStatus === 'reconnecting'
  )
}

function readPendingSessionConfig(): CustomAgentConfig | null {
  const raw = sessionStorage.getItem('ai-new-session-config')
  if (raw === null) {
    return null
  }
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed === 'object' && parsed !== null && typeof parsed.persona === 'string') {
      return parsed as CustomAgentConfig
    }
  } catch {
    return null
  }
  return null
}

function clearPendingSessionConfig() {
  sessionStorage.removeItem('ai-new-session-config')
}

function getRealtimeUnavailableMessage(
  connectionStatus: AiRealtimeConnectionStatus,
  authStatus: AiRealtimeAuthStatus,
  realtimeError: string | null,
  accessToken: string | null,
) {
  if (realtimeError !== null) {
    return realtimeError
  }
  if (authStatus === 'failed') {
    return '서버 인증이 만료되었거나 실패했습니다.'
  }
  if (accessToken === null || accessToken.trim() === '') {
    return '로그인이 필요합니다.'
  }
  if (shouldWaitForRealtime(connectionStatus, authStatus, realtimeError, accessToken)) {
    return '서버와 연결 중입니다. 잠시 후 다시 시도해 주세요.'
  }
  return '서버 연결을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.'
}

function shouldWaitForRealtime(
  connectionStatus: AiRealtimeConnectionStatus,
  authStatus: AiRealtimeAuthStatus,
  realtimeError: string | null,
  accessToken: string | null,
) {
  if (realtimeError !== null || authStatus === 'failed') {
    return false
  }
  if (accessToken === null || accessToken.trim() === '') {
    return false
  }
  return (
    isRealtimePending(connectionStatus) ||
    connectionStatus === 'idle' ||
    connectionStatus === 'closed'
  )
}
