import type { AgentRuntime } from './types'

const SIZE_NORMAL = 200
const SIZE_SITTING = 260

const SITTING_SPRITES: Record<string, string> = {
  sitting_desk: 'sit_desk',
  sitting_sofa: 'sit_sofa',
  sitting_floor_lean: 'sit_floor_lean',
  sitting_meeting: 'meeting',
}

const WALK_FRAMES = ['walk_side_01', 'walk_side_stand', 'walk_side_02', 'walk_side_stand'] as const

function getSpriteSrc(agent: AgentRuntime): string {
  const base = agent.config.spritePath
  if (agent.state in SITTING_SPRITES) return `${base}/${SITTING_SPRITES[agent.state]}.png`
  if (agent.state === 'walking') return `${base}/${WALK_FRAMES[agent.walkFrame]}.png`
  return `${base}/idle_front.png`
}

interface AgentSpriteProps {
  agent: AgentRuntime
  onArrived: (agentId: string) => void
}

export function AgentSprite({ agent, onArrived }: AgentSpriteProps) {
  const { config, position, state, transitionDuration } = agent
  const size = state === 'sitting_desk' ? SIZE_SITTING : SIZE_NORMAL

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: size,
        height: size,
        transform: `translate(${position.x - size / 2}px, ${position.y - size / 2}px)`,
        transition: state === 'walking' ? `transform ${transitionDuration}s linear` : 'none',
        zIndex: 10,
        pointerEvents: 'none',
      }}
      onTransitionEnd={() => {
        if (state === 'walking') onArrived(config.id)
      }}
    >
      <img
        src={getSpriteSrc(agent)}
        alt={config.name}
        draggable={false}
        style={{ width: '100%', height: '100%', userSelect: 'none' }}
      />
    </div>
  )
}
