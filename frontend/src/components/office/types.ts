// AgentConfig.destinations 에서 사용하는 내부 목적지 타입
export type Destination = 'desk' | 'sofa' | 'floorLean' | 'meeting' | 'calling'

// UI 버튼에서 사용하는 목적지 타입 (sofa + floorLean → rest 로 통합)
export type UIDestination = 'desk' | 'rest' | 'meeting' | 'calling'

export type AgentState =
  | 'idle'
  | 'walking'
  | 'sitting_desk'
  | 'sitting_sofa'
  | 'sitting_floor_lean'
  | 'sitting_meeting'
  | 'sitting_calling'
  | 'standing_wait' // 목적지 자리가 점유 중일 때 옆에 서 있는 상태

export type SittingState = Exclude<AgentState, 'idle' | 'walking'>

export interface Waypoint {
  x: number
  y: number
}

export interface AgentConfig {
  id: string
  name: string
  spritePath: string
  initialPosition: { x: number; y: number }
  destinations: Record<Destination, { x: number; y: number; waypoints?: Waypoint[] }>
  scale?: number
  stateScales?: Partial<Record<AgentState, number>>
}

export interface AgentRuntime {
  config: AgentConfig
  position: { x: number; y: number }
  state: AgentState
  targetState: SittingState
  walkFrame: 0 | 1 | 2 | 3
  transitionDuration: number
  pendingWaypoints: Waypoint[]
  targetPosition: Waypoint | null
  facingRight: boolean // true면 스프라이트 좌우 반전
  standWaitTarget: Waypoint | null // standing_wait 시 바라볼 목적지 좌표
}
