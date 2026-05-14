import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { HelpCircle } from 'lucide-react'
import { HoverCard, HoverCardContent, HoverCardTrigger } from './hover-card'
import { cn } from './utils'

interface HelpHintProps {
  label: string
  children: ReactNode
  className?: string
  iconClassName?: string
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  triggerTabIndex?: number
}

/**
 * 호버하면 잠깐 펼쳐지고, 클릭하면 고정되는 도움말 팝업.
 * - 호버: 열렸다가 마우스가 떠나면 닫힘.
 * - 클릭: 고정 — 다시 클릭하거나 바깥을 클릭하면 닫힘.
 * - 자동 포커스(예: 모달 진입 시)로는 열리지 않는다.
 */
export function HelpHint({
  label,
  children,
  className,
  iconClassName,
  side = 'top',
  align = 'center',
  triggerTabIndex,
}: HelpHintProps) {
  const [open, setOpen] = useState(false)
  const [pinned, setPinned] = useState(false)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const contentRef = useRef<HTMLDivElement | null>(null)
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const cancelCloseTimer = () => {
    if (closeTimerRef.current !== null) {
      clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }

  const scheduleClose = () => {
    cancelCloseTimer()
    closeTimerRef.current = setTimeout(() => {
      setOpen(false)
    }, 100)
  }

  useEffect(() => {
    if (!pinned) return

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (target === null) return
      if (triggerRef.current?.contains(target)) return
      if (contentRef.current?.contains(target)) return
      setPinned(false)
      setOpen(false)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    return () => document.removeEventListener('pointerdown', handlePointerDown)
  }, [pinned])

  useEffect(() => () => cancelCloseTimer(), [])

  const handleTriggerEnter = () => {
    cancelCloseTimer()
    setOpen(true)
  }

  const handleTriggerLeave = () => {
    if (pinned) return
    scheduleClose()
  }

  const handleTriggerClick = () => {
    cancelCloseTimer()
    if (pinned) {
      setPinned(false)
      setOpen(false)
    } else {
      setPinned(true)
      setOpen(true)
    }
  }

  const handleContentEnter = () => {
    cancelCloseTimer()
  }

  const handleContentLeave = () => {
    if (pinned) return
    scheduleClose()
  }

  return (
    <HoverCard open={open} onOpenChange={() => undefined}>
      <HoverCardTrigger asChild>
        <button
          ref={triggerRef}
          type="button"
          aria-label={label}
          tabIndex={triggerTabIndex}
          onMouseEnter={handleTriggerEnter}
          onMouseLeave={handleTriggerLeave}
          onClick={handleTriggerClick}
          className={cn(
            'text-muted-foreground hover:text-foreground inline-flex items-center justify-center rounded-full transition-colors',
            className,
          )}
        >
          <HelpCircle className={cn('h-3.5 w-3.5', iconClassName)} />
        </button>
      </HoverCardTrigger>
      <HoverCardContent
        ref={contentRef}
        side={side}
        align={align}
        sideOffset={8}
        collisionPadding={12}
        onMouseEnter={handleContentEnter}
        onMouseLeave={handleContentLeave}
        className="w-72 space-y-2 text-left text-xs leading-relaxed break-keep whitespace-normal"
      >
        {children}
      </HoverCardContent>
    </HoverCard>
  )
}
