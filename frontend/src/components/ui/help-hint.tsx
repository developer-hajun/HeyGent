import { HelpCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { HoverCard, HoverCardContent, HoverCardTrigger } from './hover-card'
import { cn } from './utils'

interface HelpHintProps {
  label: string
  children: ReactNode
  className?: string
  iconClassName?: string
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
}

export function HelpHint({
  label,
  children,
  className,
  iconClassName,
  side = 'top',
  align = 'center',
}: HelpHintProps) {
  return (
    <HoverCard openDelay={120} closeDelay={80}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          aria-label={label}
          className={cn(
            'text-muted-foreground hover:text-foreground inline-flex items-center justify-center rounded-full transition-colors',
            className,
          )}
        >
          <HelpCircle className={cn('h-3.5 w-3.5', iconClassName)} />
        </button>
      </HoverCardTrigger>
      <HoverCardContent
        side={side}
        align={align}
        sideOffset={8}
        collisionPadding={12}
        className="w-72 space-y-2 text-left text-xs leading-relaxed break-keep whitespace-normal"
      >
        {children}
      </HoverCardContent>
    </HoverCard>
  )
}
