import type { ComponentType, CSSProperties } from 'react'

export interface Agent {
  name: string
  icon: ComponentType<{ className?: string; style?: CSSProperties }>
  accent: string
  description: string
  title?: string
  role?: string
  adapterType?: string
  command?: string
  model?: string
  extraArgs?: string
  webSearchEnabled?: boolean
  bypassSandbox?: boolean
  heartbeatEnabled?: boolean
  intervalSec?: number
  profileImage?: string
  spriteId?: string
  reportsToAgentId?: string
  skills?: string[]
}
