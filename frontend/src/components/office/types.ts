export type Destination = 'desk' | 'sofa' | 'floorLean' | 'meeting' | 'calling'

export type AgentState =
  | 'idle'
  | 'walking'
  | 'sitting_desk'
  | 'sitting_sofa'
  | 'sitting_floor_lean'
  | 'sitting_meeting'
  | 'sitting_calling'

export type SittingState = Exclude<AgentState, 'idle' | 'walking'>

export interface AgentConfig {
  id: string
  name: string
  spritePath: string
  initialPosition: { x: number; y: number }
  destinations: Record<Destination, { x: number; y: number }>
}

export interface AgentRuntime {
  config: AgentConfig
  position: { x: number; y: number }
  state: AgentState
  targetState: SittingState
  walkFrame: 0 | 1 | 2 | 3
  transitionDuration: number
}
