import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router'
import { motion, AnimatePresence } from 'motion/react'
import {
  ArrowLeft,
  Send,
  Sparkles,
  Bot,
  CheckCircle2,
  Copy,
  MoreHorizontal,
  ChevronDown,
  Zap,
  Check,
} from 'lucide-react'
import { sessions, agentMeta } from '../data/sessions'
import type { Message, AgentKey } from '../data/sessions'
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover'

// Model Settings Component
function ModelSettingsContent({
  modelProvider,
  setModelProvider,
  modelName,
  setModelName,
}: {
  modelProvider: string
  setModelProvider: (value: string) => void
  modelName: string
  setModelName: (value: string) => void
}) {
  const [providerOpen, setProviderOpen] = useState(false)
  const [modelOpen, setModelOpen] = useState(false)

  const providers = [
    { value: 'OpenAI', label: 'OpenAI', description: 'GPT 시리즈' },
    { value: 'Anthropic', label: 'Anthropic', description: 'Claude 시리즈' },
    { value: 'Google', label: 'Google', description: 'Gemini 시리즈' },
    { value: 'Meta', label: 'Meta', description: 'Llama 시리즈' },
  ]

  const getModelOptions = () => {
    const modelsByProvider: Record<
      string,
      Array<{ value: string; label: string; description: string }>
    > = {
      OpenAI: [
        { value: 'GPT-4 Turbo', label: 'GPT-4 Turbo', description: '가장 강력한 모델' },
        { value: 'GPT-4', label: 'GPT-4', description: '고급 추론' },
        { value: 'GPT-3.5 Turbo', label: 'GPT-3.5 Turbo', description: '빠른 응답' },
      ],
      Anthropic: [
        { value: 'Claude 3 Opus', label: 'Claude 3 Opus', description: '최고 성능' },
        { value: 'Claude 3 Sonnet', label: 'Claude 3 Sonnet', description: '균형잡힌 성능' },
        { value: 'Claude 3 Haiku', label: 'Claude 3 Haiku', description: '빠른 응답' },
      ],
      Google: [
        { value: 'Gemini Pro', label: 'Gemini Pro', description: '전문가급' },
        { value: 'Gemini Ultra', label: 'Gemini Ultra', description: '최고급' },
      ],
      Meta: [
        { value: 'Llama 3 70B', label: 'Llama 3 70B', description: '대형 모델' },
        { value: 'Llama 3 8B', label: 'Llama 3 8B', description: '소형 모델' },
      ],
    }
    return modelsByProvider[modelProvider] || []
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-foreground mb-3 text-sm font-semibold">모델 설정</h3>
      </div>

      {/* Provider Selection */}
      <div>
        <label className="text-foreground mb-2 block text-xs font-medium">공급자</label>
        <Popover open={providerOpen} onOpenChange={setProviderOpen}>
          <PopoverTrigger asChild>
            <button className="border-border text-foreground hover:bg-muted/30 flex w-full items-center justify-between rounded-xl border bg-white px-3 py-2.5 text-sm transition-colors">
              <span>{modelProvider}</span>
              <ChevronDown className="text-muted-foreground h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-64 rounded-2xl p-2" align="start">
            <div className="space-y-1">
              {providers.map((provider) => (
                <button
                  key={provider.value}
                  onClick={() => {
                    setModelProvider(provider.value)
                    setProviderOpen(false)
                  }}
                  className="hover:bg-muted flex w-full items-start justify-between rounded-xl px-3 py-2.5 text-left transition-colors"
                >
                  <div className="flex-1">
                    <div className="text-foreground mb-0.5 text-sm font-medium">
                      {provider.label}
                    </div>
                    <div className="text-muted-foreground text-xs">{provider.description}</div>
                  </div>
                  {modelProvider === provider.value && (
                    <Check className="text-primary mt-0.5 h-4 w-4 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Model Name Selection */}
      <div>
        <label className="text-foreground mb-2 block text-xs font-medium">모델명</label>
        <Popover open={modelOpen} onOpenChange={setModelOpen}>
          <PopoverTrigger asChild>
            <button className="border-border text-foreground hover:bg-muted/30 flex w-full items-center justify-between rounded-xl border bg-white px-3 py-2.5 text-sm transition-colors">
              <span>{modelName}</span>
              <ChevronDown className="text-muted-foreground h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-64 rounded-2xl p-2" align="start">
            <div className="space-y-1">
              {getModelOptions().map((model) => (
                <button
                  key={model.value}
                  onClick={() => {
                    setModelName(model.value)
                    setModelOpen(false)
                  }}
                  className="hover:bg-muted flex w-full items-start justify-between rounded-xl px-3 py-2.5 text-left transition-colors"
                >
                  <div className="flex-1">
                    <div className="text-foreground mb-0.5 text-sm font-medium">{model.label}</div>
                    <div className="text-muted-foreground text-xs">{model.description}</div>
                  </div>
                  {modelName === model.value && (
                    <Check className="text-primary mt-0.5 h-4 w-4 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Current Selection Info */}
      <div className="border-border border-t pt-2">
        <p className="text-muted-foreground text-xs">
          현재 선택:{' '}
          <span className="text-foreground font-medium">
            {modelProvider} - {modelName}
          </span>
        </p>
      </div>
    </div>
  )
}

function MessageCard({ content }: { content: string }) {
  return (
    <pre className="bg-muted/60 border-border text-foreground/80 mt-2.5 overflow-x-auto rounded-xl border px-4 py-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
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
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      {!isUser && (
        <div
          className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
          style={{ backgroundColor: meta ? `${meta.color}18` : '#f1f5f9' }}
        >
          {AgentIcon ? (
            <AgentIcon style={{ color: meta!.color, width: '15px', height: '15px' }} />
          ) : (
            <Bot className="text-primary h-4 w-4" />
          )}
        </div>
      )}

      <div className={`flex max-w-[75%] flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Agent name */}
        {!isUser && meta && (
          <span className="px-1 text-xs font-semibold" style={{ color: meta.color }}>
            {meta.name}
          </span>
        )}

        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-primary rounded-tr-sm text-white'
              : 'border-border text-foreground rounded-tl-sm border bg-white'
          }`}
        >
          {/* Render simple bold markers */}
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

        {/* Time + copy */}
        <div
          className={`flex items-center gap-1.5 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
        >
          <span className="text-muted-foreground text-xs">{msg.time}</span>
          {isUser && <CheckCircle2 className="text-primary/50 h-3 w-3" />}
          {!isUser && (
            <button className="hover:bg-muted text-muted-foreground flex h-5 w-5 items-center justify-center rounded opacity-0 transition-colors group-hover:opacity-100">
              <Copy className="h-2.5 w-2.5" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export function SessionChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const session = sessions.find((s) => s.id === sessionId)

  const [messages, setMessages] = useState<Message[]>(session?.messages ?? [])
  const [inputValue, setInputValue] = useState('')
  const [sending, setSending] = useState(false)
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false)
  const [reasoningStrength, setReasoningStrength] = useState<'Low' | 'Medium' | 'High'>('Medium')
  const [modelProvider, setModelProvider] = useState('OpenAI')
  const [modelName, setModelName] = useState('GPT-4 Turbo')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const defaultModels: Record<string, string> = {
    OpenAI: 'GPT-4 Turbo',
    Anthropic: 'Claude 3 Opus',
    Google: 'Gemini Pro',
    Meta: 'Llama 3 70B',
  }

  const handleProviderChange = (provider: string) => {
    setModelProvider(provider)
    setModelName(defaultModels[provider] || 'GPT-4 Turbo')
  }

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!session) {
    return (
      <div className="bg-background flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground text-sm">세션을 찾을 수 없습니다.</p>
          <button
            onClick={() => navigate('/')}
            className="text-primary mt-3 text-xs hover:underline"
          >
            메인으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  const agentInfo = agentMeta[session.agentKey]
  const AgentIcon = agentInfo.icon

  const handleSend = () => {
    const text = inputValue.trim()
    if (!text || sending) return

    const userMsg: Message = {
      id: `new-${Date.now()}`,
      role: 'user',
      time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
      text,
    }
    setMessages((prev) => [...prev, userMsg])
    setInputValue('')
    setSending(true)

    // Mock agent reply
    setTimeout(() => {
      const replyMsg: Message = {
        id: `reply-${Date.now()}`,
        role: 'agent',
        agent: session.agentKey,
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
    <div className="bg-background flex flex-1 flex-col overflow-hidden">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="border-border flex flex-shrink-0 items-center gap-3 border-b bg-white px-5 py-3">
        <button
          onClick={() => navigate('/')}
          className="hover:bg-muted text-muted-foreground hover:text-foreground flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div
          className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
          style={{ backgroundColor: `${agentInfo.color}18` }}
        >
          <AgentIcon style={{ color: agentInfo.color, width: '17px', height: '17px' }} />
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-sm font-semibold">{session.title}</p>
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground text-xs">{session.time}</span>
            <span className="text-muted-foreground/40 text-xs">·</span>
            <span className="text-xs font-medium" style={{ color: agentInfo.color }}>
              {agentInfo.shortName}
            </span>
          </div>
        </div>

        {/* Reasoning Strength Selector */}
        <Popover>
          <PopoverTrigger asChild>
            <button className="hover:bg-muted border-border flex items-center gap-1.5 rounded-lg border px-3 py-1.5 transition-colors">
              <Zap className="text-primary h-3.5 w-3.5" />
              <span className="text-foreground text-xs font-medium">{reasoningStrength}</span>
              <ChevronDown className="text-muted-foreground h-3 w-3" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-48 p-2" align="end">
            <div className="space-y-1">
              <p className="text-foreground px-2 py-1 text-xs font-semibold">추론 강도</p>
              {(['Low', 'Medium', 'High'] as const).map((strength) => (
                <button
                  key={strength}
                  onClick={() => setReasoningStrength(strength)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    reasoningStrength === strength
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'hover:bg-muted text-foreground'
                  }`}
                >
                  {strength}
                </button>
              ))}
            </div>
          </PopoverContent>
        </Popover>

        {/* Model Settings */}
        <Popover open={modelSettingsOpen} onOpenChange={setModelSettingsOpen}>
          <PopoverTrigger asChild>
            <button className="hover:bg-muted text-muted-foreground flex h-8 w-8 items-center justify-center rounded-lg transition-colors">
              <MoreHorizontal className="h-4 w-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-80 p-4" align="end">
            <ModelSettingsContent
              modelProvider={modelProvider}
              setModelProvider={handleProviderChange}
              modelName={modelName}
              setModelName={setModelName}
            />
          </PopoverContent>
        </Popover>
      </div>

      {/* ── Message list ───────────────────────────────── */}
      <div className="flex-1 space-y-5 overflow-y-auto px-6 py-6">
        {/* Date separator */}
        <div className="flex items-center gap-3">
          <div className="bg-border h-px flex-1" />
          <span className="text-muted-foreground flex-shrink-0 px-2 text-xs">
            {session.time.startsWith('오늘') ? '오늘' : '어제'}
          </span>
          <div className="bg-border h-px flex-1" />
        </div>

        {messages.map((msg) => (
          <ChatMessage key={msg.id} msg={msg} />
        ))}

        {/* Typing indicator */}
        <AnimatePresence>
          {sending && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="flex gap-3"
            >
              <div
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl shadow-sm"
                style={{ backgroundColor: `${agentInfo.color}18` }}
              >
                <AgentIcon style={{ color: agentInfo.color, width: '15px', height: '15px' }} />
              </div>
              <div className="border-border flex items-center gap-1.5 rounded-2xl rounded-tl-sm border bg-white px-4 py-3 shadow-sm">
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

      {/* ── Input bar ──────────────────────────────────── */}
      <div className="border-border flex-shrink-0 border-t bg-white px-5 py-4">
        <div className="bg-background border-border overflow-hidden rounded-2xl border shadow-sm transition-shadow hover:shadow-md">
          <div className="flex items-center gap-3 px-4 py-3">
            <Sparkles className="text-primary/50 h-4 w-4 flex-shrink-0" />
            <input
              ref={inputRef}
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
              className="bg-primary hover:bg-primary/90 flex-shrink-0 rounded-xl p-2 text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <p className="text-muted-foreground mt-2 text-center text-xs">
          이 세션은 <strong>{agentInfo.name}</strong>과 진행된 대화입니다
        </p>
      </div>
    </div>
  )
}
