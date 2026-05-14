import type { ReactNode } from 'react'
import { TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useIsMobile } from '@/components/ui/use-mobile'

export interface PageTabItem {
  value: string
  label: ReactNode
}

interface PageTabBarProps {
  items: PageTabItem[]
  value?: string
  onValueChange?: (value: string) => void
  align?: 'center' | 'start'
}

export function PageTabBar({ items, value, onValueChange, align = 'center' }: PageTabBarProps) {
  const isMobile = useIsMobile()

  if (isMobile && value !== undefined && onValueChange) {
    return (
      <select
        value={value}
        onChange={(event) => onValueChange(event.target.value)}
        className="border-border bg-background focus:ring-ring h-9 rounded-md border px-2 py-1 text-base focus:ring-1 focus:outline-none"
      >
        {items.map((item) => (
          <option key={item.value} value={item.value}>
            {typeof item.label === 'string' ? item.label : item.value}
          </option>
        ))}
      </select>
    )
  }

  return (
    <TabsList variant="line" className={align === 'start' ? 'justify-start' : undefined}>
      {items.map((item) => (
        <TabsTrigger key={item.value} value={item.value}>
          {item.label}
        </TabsTrigger>
      ))}
    </TabsList>
  )
}
