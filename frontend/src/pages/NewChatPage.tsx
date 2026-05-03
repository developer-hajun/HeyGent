import { Sparkles, Send, Code, Calendar, Apple, Activity, Mic, Bot } from 'lucide-react'
import { motion } from 'motion/react'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { sendSessionMessageCreate } from '@/components/chat/aiChatCommands'

const suggestedPrompts = [
  {
    text: '이 PR 검토해줘',
    icon: Code,
    bg: 'hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600',
  },
  {
    text: '오후 5시에 알려줘',
    icon: Calendar,
    bg: 'hover:bg-violet-50 hover:border-violet-200 hover:text-violet-600',
  },
  {
    text: '저녁 메뉴 추천해줘',
    icon: Apple,
    bg: 'hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-600',
  },
  {
    text: '운동 끝나면 알려줘',
    icon: Activity,
    bg: 'hover:bg-orange-50 hover:border-orange-200 hover:text-orange-600',
  },
]

export function NewChatPage() {
  const [inputValue, setInputValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleVoiceInput = () => {
    setIsRecording(!isRecording)
  }

  const handleSend = async () => {
    const content = inputValue.trim()
    if (!content || isSending) return
    setIsSending(true)
    setSendError(null)

    try {
      // 새 채팅의 첫 입력도 같은 WebSocket command를 사용한다.
      // accepted 이후 서버가 확정한 sessionId로 이동해야 optimistic 세션 ID가 URL에 남지 않는다.
      const accepted = await sendSessionMessageCreate({ content })
      navigate(`/session/${accepted.sessionId}`)
    } catch (error) {
      setSendError(error instanceof Error ? error.message : '새 채팅을 시작하지 못했습니다.')
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
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
                onClick={handleVoiceInput}
                className={`shrink-0 rounded-xl p-2.5 transition-colors ${
                  isRecording
                    ? 'animate-pulse bg-red-500 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                title="음성 입력"
              >
                <Mic className="h-4 w-4" />
              </button>
              <button
                onClick={handleSend}
                className="bg-primary hover:bg-primary/90 shrink-0 rounded-xl p-2 text-white transition-colors disabled:opacity-40"
                disabled={!inputValue.trim() || isSending}
              >
                <Send className={`h-4 w-4 ${isSending ? 'animate-pulse' : ''}`} />
              </button>
            </div>
            {sendError && <p className="text-destructive px-5 pb-2 text-xs">{sendError}</p>}

            {/* Divider */}
            <div className="border-border/60 mx-5 border-t" />

            {/* Prompt chips */}
            <div className="flex flex-wrap items-center gap-2 px-5 py-3">
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInputValue(prompt.text)}
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
