export type AgentState = 'idle' | 'walking' | 'sitting'

export interface AgentConfig {
  id: string
  name: string
  spritePath: string
  initialPosition: { x: number; y: number }
  deskPosition: { x: number; y: number }
}

export interface AgentRuntime {
  config: AgentConfig
  position: { x: number; y: number }
  state: AgentState
  walkFrame: 0 | 1
  transitionDuration: number
}
