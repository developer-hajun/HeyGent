import { Loader2, Send, Sparkles } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

type ChatComposerProps = {
  disabled?: boolean
  isSending?: boolean
  placeholder?: string
  onSend: (content: string) => void
}

export function ChatComposer({
  disabled = false,
  isSending = false,
  placeholder = '메시지를 입력하세요...',
  onSend,
}: ChatComposerProps) {
  const [value, setValue] = useState('')

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
    <div className="border-border bg-background/95 supports-[backdrop-filter]:bg-background/80 border-t px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="border-border bg-card focus-within:ring-ring/20 flex min-h-12 flex-1 items-end gap-2 rounded-2xl border px-3 py-2 shadow-sm focus-within:ring-2">
          <Sparkles className="text-primary/70 mt-1 h-4 w-4 shrink-0" />
          <textarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="text-foreground placeholder:text-muted-foreground max-h-36 min-h-8 flex-1 resize-none bg-transparent py-1 text-sm outline-none disabled:opacity-60"
          />
          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || disabled || isSending}
            aria-label="메시지 보내기"
            className="bg-primary hover:bg-primary/90 text-primary-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-colors disabled:opacity-40"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
