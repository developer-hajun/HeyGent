import type { ComponentType, CSSProperties } from 'react'

export interface Agent {
  name: string
  icon: ComponentType<{ className?: string; style?: CSSProperties }>
  accent: string
  description: string
  skills?: string[]
}
