import type { AgentRuntime } from './types'

const SIZE_NORMAL = 200
const SIZE_SITTING = 260

function getSpriteSrc(agent: AgentRuntime): string {
  const base = agent.config.spritePath
  if (agent.state === 'sitting') return `${base}/sit_desk.png`
  if (agent.state === 'walking') return `${base}/walk_side_0${agent.walkFrame + 1}.png`
  return `${base}/idle_front.png`
}

interface AgentSpriteProps {
  agent: AgentRuntime
  onArrived: (agentId: string) => void
}

export function AgentSprite({ agent, onArrived }: AgentSpriteProps) {
  const { config, position, state, transitionDuration } = agent
  const size = state === 'sitting' ? SIZE_SITTING : SIZE_NORMAL

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
