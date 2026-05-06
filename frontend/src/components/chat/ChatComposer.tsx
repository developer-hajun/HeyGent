import {
  AudioLines,
  ChevronRight,
  FileImage,
  Globe,
  ImagePlus,
  Mic,
  MoreHorizontal,
  Plus,
  Search,
  Send,
} from 'lucide-react'
import { useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

type ChatComposerProps = {
  disabled?: boolean
  isSending?: boolean
  placeholder?: string
  onSend: (content: string) => void
  onVoiceMode?: () => void
}

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

export function ChatComposer({
  disabled = false,
  isSending = false,
  placeholder = '무엇이든 물어보세요...',
  onSend,
  onVoiceMode,
}: ChatComposerProps) {
  const [value, setValue] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [attachOpen, setAttachOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (textarea === null) return

    textarea.style.height = '0px'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 144)}px`
  }, [value])

  const submit = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled || isSending) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="bg-background/95 supports-backdrop-filter:bg-background/80 px-4 py-2 backdrop-blur">
      <div className="mx-auto max-w-3xl">
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
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="text-foreground placeholder:text-muted-foreground max-h-36 min-h-6 flex-1 resize-none bg-transparent py-0 text-[15px] outline-none disabled:opacity-60"
            />
            <button
              type="button"
              onClick={() => setIsRecording((r) => !r)}
              aria-label={isRecording ? '음성 입력 중지' : '음성 입력 시작'}
              className={`shrink-0 rounded-2xl p-2.5 transition-colors ${
                isRecording
                  ? 'animate-pulse bg-red-500 text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              <Mic className="h-4 w-4" />
            </button>
            {value.trim() ? (
              <button
                type="button"
                onClick={submit}
                disabled={disabled || isSending}
                aria-label="메시지 보내기"
                className="bg-primary hover:bg-primary/90 shrink-0 rounded-2xl p-2 text-white transition-colors disabled:opacity-40"
              >
                <Send className={`h-4 w-4 ${isSending ? 'animate-pulse' : ''}`} />
              </button>
            ) : (
              <button
                type="button"
                onClick={onVoiceMode}
                aria-label="음성 대화 모드"
                title="음성 대화 모드"
                className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-2xl p-2 text-white transition-colors"
              >
                <AudioLines className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
