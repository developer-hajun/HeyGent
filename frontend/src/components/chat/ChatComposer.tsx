import {
  AudioLines,
  ChevronRight,
  FileImage,
  Globe,
  ImagePlus,
  ListTodo,
  Mic,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Square,
  X,
} from 'lucide-react'
import { useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

type ChatComposerProps = {
  disabled?: boolean
  isSending?: boolean
  placeholder?: string
  onSend: (content: string) => void
  onClearSelectedWork?: () => void
  onSelectWorkClick?: () => void
  onStop?: () => void
  onVoiceMode?: () => void
  draftValue?: string | null
  statusMessage?: string | null
  selectedWorkLabel?: string | null
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
  onClearSelectedWork,
  onSelectWorkClick,
  onStop,
  onVoiceMode,
  draftValue = null,
  statusMessage = null,
  selectedWorkLabel = null,
}: ChatComposerProps) {
  const [value, setValue] = useState(draftValue ?? '')
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
    <div className="bg-background/95 supports-backdrop-filter:bg-background/80 px-4 pt-2 pb-8 backdrop-blur sm:pb-10">
      <div className="mx-auto max-w-3xl">
        <div className="border-border bg-card overflow-hidden rounded-2xl border shadow-sm transition-shadow duration-200 hover:shadow-md">
          {/* Input row */}
          {selectedWorkLabel && (
            <div className="border-border/60 bg-muted/20 flex items-center gap-2 border-b px-5 py-2 text-xs">
              <ListTodo className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
              <span className="text-muted-foreground">연결된 작업</span>
              <span className="text-foreground min-w-0 flex-1 truncate font-medium">
                {selectedWorkLabel}
              </span>
              {selectedWorkLabel && (
                <button
                  type="button"
                  onClick={onClearSelectedWork}
                  aria-label="연결된 작업 해제"
                  className="text-muted-foreground hover:text-foreground rounded-sm p-1"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
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
                <div className="border-border/60 my-1 border-t" />
                <button
                  type="button"
                  onClick={() => {
                    setAttachOpen(false)
                    onSelectWorkClick?.()
                  }}
                  className="hover:bg-muted flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors"
                >
                  <ListTodo className="text-muted-foreground h-4 w-4 shrink-0" />
                  <span className="text-foreground flex-1 text-sm">기존 작업 선택</span>
                </button>
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
            {isSending ? (
              <button
                type="button"
                onClick={onStop}
                aria-label="응답 중지"
                title="응답 중지"
                className="border-foreground text-foreground hover:bg-muted shrink-0 rounded-2xl border-2 bg-white p-2.5 transition-colors"
              >
                <Square className="h-4 w-4 fill-current" />
              </button>
            ) : value.trim() ? (
              <button
                type="button"
                onClick={submit}
                disabled={disabled}
                aria-label="메시지 보내기"
                className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-2xl p-2.5 text-white transition-colors disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onVoiceMode}
                aria-label="음성 대화 모드"
                title="음성 대화 모드"
                className="bg-foreground hover:bg-foreground/85 shrink-0 rounded-2xl p-2.5 text-white transition-colors"
              >
                <AudioLines className="h-4 w-4" />
              </button>
            )}
          </div>
          {statusMessage && (
            <p className="text-muted-foreground border-border/60 border-t px-5 py-2 text-xs">
              {statusMessage}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
