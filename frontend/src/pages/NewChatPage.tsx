import {
  Activity,
  Apple,
  AudioLines,
  Bot,
  Calendar,
  ChevronRight,
  Code,
  FileImage,
  Globe,
  ImagePlus,
  Mic,
  MoreHorizontal,
  Plus,
  Search,
  Send,
} from 'lucide-react'
import { motion } from 'motion/react'
import { useLayoutEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  type AiRealtimeAuthStatus,
  type AiRealtimeConnectionStatus,
  getFramePayload,
  getStringField,
} from '@/realtime/aiRealtimeTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'
import { useSessionStore } from '@/store/useSessionStore'
import type { CustomAgentConfig } from '@/components/session/NewSessionModal'
import { agentProfilesToPanelItems, createDefaultSessionAgents } from '@/apis/agents'
import { createClientMessageId } from '@/utils/requestId'

const suggestedPrompts = [
  { text: '이 PR 검토해줘', icon: Code },
  { text: '오후 5시에 알려줘', icon: Calendar },
  { text: '저녁 메뉴 추천해줘', icon: Apple },
  { text: '운동 끝나면 알려줘', icon: Activity },
]

const attachMenuItems = [
  { icon: FileImage, label: '사진 및 파일 추가', hasArrow: false },
  { icon: FileImage, label: '최근 파일', hasArrow: true },
  null,
  { icon: ImagePlus, label: '이미지 만들기', hasArrow: false },
  { icon: Search, label: '심층 리서치', hasArrow: false },
  { icon: Globe, label: '웹 검색', hasArrow: false },
  null,
  { icon: MoreHorizontal, label: '더 보기', hasArrow: true },
]

export function NewChatPage() {
  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [attachOpen, setAttachOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (textarea === null) return
    textarea.style.height = '0px'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`
  }, [inputValue])
  const navigate = useNavigate()
  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const accessToken = useAuthStore((state) => state.accessToken)
  const sendMessage = useChatStore((state) => state.sendMessage)
  const updateSession = useChatStore((state) => state.updateSession)
  const setAgentPanelsForSession = useSessionStore((state) => state.setAgentPanelsForSession)
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
      const clientMessageId = createClientMessageId()
      const pendingSessionId = `pending_session_${clientMessageId}`
      const pendingConfig = readPendingSessionConfig()
      const pendingSettings =
        pendingConfig === null
          ? undefined
          : {
              ...(pendingConfig.persona.trim()
                ? { systemPrompt: pendingConfig.persona.trim() }
                : {}),
              ...(pendingConfig.model.trim() ? { model: pendingConfig.model.trim() } : {}),
              delegationPolicy: pendingConfig.delegationPolicy,
            }
      // 첫 대화는 아직 서버 세션 id가 없어서 accepted 응답 전까지는 pending 세션을 화면에 보여 준다.
      // sendMessage가 같은 clientMessageId로 optimistic 메시지를 먼저 넣기 때문에 즉시 스피너가 렌더링된다.
      const acceptedPromise = sendMessage({
        content,
        clientMessageId,
        settings: pendingSettings,
        inputPayload:
          pendingConfig === null
            ? undefined
            : {
                sessionConfigSnapshot: {
                  agentName: pendingConfig.agentName,
                  persona: pendingConfig.persona,
                  callName: pendingConfig.callName,
                  capabilities: pendingConfig.capabilities,
                  model: pendingConfig.model,
                  delegationPolicy: pendingConfig.delegationPolicy,
                  instructionsEntryFile: pendingConfig.instructionsEntryFile,
                  instructionsMode: pendingConfig.instructionsMode,
                  instructionsRootPath: pendingConfig.instructionsRootPath,
                  instructionsFiles: pendingConfig.instructionsFiles,
                  profileImage: pendingConfig.profileImage,
                  profileImageProvided: pendingConfig.profileImage !== null,
                  seedDefaultAgents: pendingConfig.seedDefaultAgents === true,
                },
              },
      })
      navigate(`/session/${pendingSessionId}`)
      const acceptedFrame = await acceptedPromise
      const payload = getFramePayload(acceptedFrame)
      const acceptedSessionId =
        getStringField(payload, 'session_id', 'sessionId') ??
        getStringField(acceptedFrame, 'session_id', 'sessionId')

      if (acceptedSessionId === undefined) {
        throw new Error('accepted 응답에 sessionId가 없습니다.')
      }

      if (pendingConfig !== null) {
        if (pendingConfig.seedDefaultAgents) {
          const profiles = await createDefaultSessionAgents(acceptedSessionId)
          setAgentPanelsForSession(acceptedSessionId, agentProfilesToPanelItems(profiles))
        }
        if (!pendingConfig.seedDefaultAgents) {
          void updateSession({
            sessionId: acceptedSessionId,
            metadataPatch: {
              ui: {
                agentName: pendingConfig.agentName,
                callName: pendingConfig.callName,
                agentCapabilities: pendingConfig.capabilities,
                agentProfileImage: pendingConfig.profileImage,
                instructionsEntryFile: pendingConfig.instructionsEntryFile,
                instructionsMode: pendingConfig.instructionsMode,
                instructionsRootPath: pendingConfig.instructionsRootPath,
                instructionsFiles: pendingConfig.instructionsFiles,
              },
            },
          }).catch(() => {
            // 실행 중 세션은 표시 설정 갱신이 잠시 거절될 수 있다. 채팅 시작 흐름은 계속 진행한다.
          })
        }
      }

      navigate(`/session/${acceptedSessionId}`, { replace: true })
      clearPendingSessionConfig()
    } catch (error) {
      setSendError(error instanceof Error ? error.message : '새 채팅을 시작하지 못했습니다.')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
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
            <div className="flex items-center gap-3 px-5 py-2">
              <Popover open={attachOpen} onOpenChange={setAttachOpen}>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    aria-label="파일 또는 이미지 추가"
                    className="bg-muted text-muted-foreground hover:bg-muted/80 shrink-0 rounded-full p-1 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  side="top"
                  align="start"
                  sideOffset={8}
                  className="w-52 rounded-2xl p-1.5"
                >
                  {attachMenuItems.map((item, i) =>
                    item === null ? (
                      <div key={i} className="border-border/60 my-1 border-t" />
                    ) : (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => setAttachOpen(false)}
                        className="hover:bg-muted flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors"
                      >
                        <item.icon className="text-muted-foreground h-4 w-4 shrink-0" />
                        <span className="text-foreground flex-1 text-sm">{item.label}</span>
                        {item.hasArrow && (
                          <ChevronRight className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                        )}
                      </button>
                    ),
                  )}
                </PopoverContent>
              </Popover>
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="무엇이든 물어보세요..."
                rows={1}
                autoFocus
                className="text-foreground placeholder:text-muted-foreground max-h-36 min-h-6 flex-1 resize-none bg-transparent py-0 text-[15px] outline-none"
              />
              <button
                type="button"
                onClick={handleVoiceInput}
                aria-label={isRecording ? '음성 입력 중지' : '음성 입력 시작'}
                className={`shrink-0 rounded-2xl p-2.5 transition-colors ${
                  isRecording
                    ? 'animate-pulse bg-red-500 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                <Mic className="h-4 w-4" />
              </button>
              {inputValue.trim() ? (
                <button
                  type="button"
                  onClick={() => void handleSend()}
                  aria-label="새 대화 메시지 보내기"
                  disabled={isSending || commandClient === null}
                  className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-2xl p-2 text-white transition-colors disabled:opacity-40"
                >
                  <Send className={`h-4 w-4 ${isSending ? 'animate-pulse' : ''}`} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate('/session/voice', { state: { voiceMode: true } })}
                  aria-label="음성 대화 모드"
                  title="음성 대화 모드"
                  className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-2xl p-2 text-white transition-colors"
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
          </div>
        </motion.div>

        {/* Suggested prompts */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.16 }}
          className="flex flex-wrap items-center justify-center gap-2"
        >
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt.text}
              type="button"
              onClick={() => setInputValue(prompt.text)}
              aria-label={`추천 프롬프트 선택: ${prompt.text}`}
              className="bg-card border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[13px] transition-colors"
            >
              <prompt.icon className="h-3.5 w-3.5 shrink-0" />
              <span>{prompt.text}</span>
            </button>
          ))}
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
      const value = parsed as Partial<CustomAgentConfig>
      const instructionsFiles =
        typeof value.instructionsFiles === 'object' &&
        value.instructionsFiles !== null &&
        !Array.isArray(value.instructionsFiles)
          ? Object.fromEntries(
              Object.entries(value.instructionsFiles).filter(
                (entry): entry is [string, string] =>
                  typeof entry[0] === 'string' && typeof entry[1] === 'string',
              ),
            )
          : {}
      return {
        agentName: typeof value.agentName === 'string' ? value.agentName : '',
        seedDefaultAgents: value.seedDefaultAgents === true,
        persona: parsed.persona,
        callName: typeof value.callName === 'string' ? value.callName : '',
        capabilities: typeof value.capabilities === 'string' ? value.capabilities : '',
        profileImage: typeof value.profileImage === 'string' ? value.profileImage : null,
        model: typeof value.model === 'string' ? value.model : '',
        instructionsEntryFile:
          typeof value.instructionsEntryFile === 'string'
            ? value.instructionsEntryFile
            : 'AGENTS.md',
        instructionsMode: value.instructionsMode === 'external' ? 'external' : 'managed',
        instructionsRootPath:
          typeof value.instructionsRootPath === 'string' ? value.instructionsRootPath : '',
        instructionsFiles,
        delegationPolicy:
          typeof value.delegationPolicy === 'object' &&
          value.delegationPolicy !== null &&
          typeof value.delegationPolicy.canDelegate === 'boolean'
            ? {
                canDelegate: value.delegationPolicy.canDelegate,
                ...(typeof value.delegationPolicy.maxWorkerDepth === 'number'
                  ? { maxWorkerDepth: value.delegationPolicy.maxWorkerDepth }
                  : {}),
              }
            : { canDelegate: false },
      }
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
