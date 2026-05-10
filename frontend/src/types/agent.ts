import type { ComponentType, CSSProperties } from 'react'

export interface Agent {
  profileId?: string
  templateKey?: string
  instructionBundleId?: string
  name: string
  icon: ComponentType<{ className?: string; style?: CSSProperties }>
  accent: string
  description: string
  instructions?: string
  instructionsEntryFile?: string
  instructionsFiles?: Record<string, string>
  instructionsMode?: 'managed' | 'external'
  instructionsRootPath?: string
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
