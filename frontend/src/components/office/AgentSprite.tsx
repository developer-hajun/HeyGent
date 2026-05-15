import { useState, useEffect } from 'react'
import type { AgentRuntime } from './types'
import type { AgentVisualizationInfo } from './types'

const SPAWN_KEYFRAMES = `
@keyframes spawnBulb {
  0%   { opacity: 0; transform: scale(0.2); }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes workingPulse {
  0%, 100% { opacity: 0.95; transform: scale(1); }
  50%       { opacity: 0.5;  transform: scale(0.88); }
}
`

function injectSpawnStyles() {
  if (document.getElementById('agent-spawn-style')) return
  const el = document.createElement('style')
  el.id = 'agent-spawn-style'
  el.textContent = SPAWN_KEYFRAMES
  document.head.appendChild(el)
}

const SIZE_NORMAL = 200
const SIZE_SITTING = 260

const SITTING_SPRITES: Record<string, string> = {
  sitting_desk: 'sit_desk',
  sitting_sofa: 'sit_sofa',
  sitting_floor_lean: 'sit_floor_lean',
  sitting_meeting: 'meeting',
  sitting_calling: 'calling',
  standing_wait: 'walk_side_stand',
}

const WALK_FRAMES = ['walk_side_01', 'walk_side_stand', 'walk_side_02', 'walk_side_stand'] as const

const TASK_STATUS_LABEL: Record<string, string> = {
  pending: '대기 중',
  in_progress: '진행 중',
  completed: '완료',
  failed: '실패',
}

const TASK_STATUS_COLOR: Record<string, string> = {
  pending: '#fde047',
  in_progress: '#93c5fd',
  completed: '#86efac',
  failed: '#fca5a5',
}

function getSpriteSrc(agent: AgentRuntime): string {
  const base = agent.config.spritePath
  const sittingMap = agent.config.sittingSprites
    ? { ...SITTING_SPRITES, ...agent.config.sittingSprites }
    : SITTING_SPRITES
  if (agent.state in sittingMap) return `${base}/${sittingMap[agent.state]}.png`
  const frames = agent.config.walkFrames ?? WALK_FRAMES
  if (agent.state === 'walking') return `${base}/${frames[agent.walkFrame]}.png`
  return `${base}/idle_front.png`
}

interface AgentSpriteProps {
  agent: AgentRuntime
  onArrived: (agentId: string) => void
  onClick?: (agentId: string) => void
  hoverInfo?: AgentVisualizationInfo
  isSelected?: boolean
  isSpawning?: boolean
}

export function AgentSprite({
  agent,
  onArrived,
  onClick,
  hoverInfo,
  isSelected,
  isSpawning,
}: AgentSpriteProps) {
  const [isHovered, setIsHovered] = useState(false)
  useEffect(() => {
    injectSpawnStyles()
  }, [])
  const { config, position, state, transitionDuration } = agent
  const scale = (config.scale ?? 1) * (config.stateScales?.[state] ?? 1)
  const size = (state === 'sitting_desk' ? SIZE_SITTING : SIZE_NORMAL) * scale
  const isInteractive = !!onClick

  const showTooltip = isHovered && !!hoverInfo

  let zIndex = 10
  if (isSelected && isHovered) zIndex = 30
  else if (isSelected) zIndex = 25
  else if (isHovered) zIndex = 20

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
        zIndex,
        pointerEvents: isInteractive ? 'auto' : 'none',
        cursor: isInteractive ? 'pointer' : 'default',
      }}
      onTransitionEnd={(e) => {
        if (state === 'walking' && e.propertyName === 'transform') onArrived(config.id)
      }}
      onClick={() => onClick?.(config.id)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 스폰 전구 — 에이전트 등장 시 머리 위에 💡 아이콘이 팝업 */}
      {isSpawning && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: 6,
            pointerEvents: 'none',
            zIndex: 40,
          }}
        >
          <span
            style={{
              display: 'block',
              fontSize: 24,
              lineHeight: 1,
              animation: 'spawnBulb 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both',
              filter: 'drop-shadow(0 0 8px rgba(253, 224, 71, 0.9))',
            }}
          >
            💡
          </span>
        </div>
      )}

      {/* 작업 중 전구 — CEO가 ceo_work(sitting_work) 상태일 때 상시 표시 */}
      {!isSpawning && agent.config.id === 'ceo' && agent.state === 'sitting_work' && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: 6,
            pointerEvents: 'none',
            zIndex: 40,
          }}
        >
          <span
            style={{
              display: 'block',
              fontSize: 22,
              lineHeight: 1,
              animation: 'workingPulse 2s ease-in-out infinite',
              filter: 'drop-shadow(0 0 8px rgba(253, 224, 71, 0.85))',
            }}
          >
            💡
          </span>
        </div>
      )}

      {/* 호버 툴팁 */}
      {showTooltip && (
        <div
          style={{
            position: 'absolute',
            bottom: '100%',
            left: '65%',
            transform: 'translateX(-50%)',
            marginBottom: 12,
            zIndex: 50,
            pointerEvents: 'none',
            minWidth: 190,
          }}
        >
          <div
            style={{
              background: 'rgba(8, 8, 18, 0.90)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 12,
              padding: '10px 14px',
              backdropFilter: 'blur(12px)',
              boxShadow: '0 6px 28px rgba(0,0,0,0.6)',
            }}
          >
            {/* 이름 + 역할 */}
            <div style={{ marginBottom: 8 }}>
              <div style={{ color: 'white', fontSize: 13, fontWeight: 700 }}>{hoverInfo.name}</div>
              <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11, marginTop: 2 }}>
                {hoverInfo.role}
              </div>
            </div>

            {/* 현재 작업 */}
            {hoverInfo.currentTask && (
              <div
                style={{
                  borderTop: '1px solid rgba(255,255,255,0.08)',
                  paddingTop: 8,
                }}
              >
                <div
                  style={{
                    color: 'rgba(255,255,255,0.35)',
                    fontSize: 10,
                    marginBottom: 4,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  현재 작업
                </div>
                <div style={{ color: 'white', fontSize: 12, fontWeight: 600 }}>
                  {hoverInfo.currentTask.title}
                </div>
                <div
                  style={{
                    color:
                      TASK_STATUS_COLOR[hoverInfo.currentTask.status] ?? 'rgba(255,255,255,0.5)',
                    fontSize: 11,
                    marginTop: 3,
                  }}
                >
                  ● {TASK_STATUS_LABEL[hoverInfo.currentTask.status]}
                </div>
              </div>
            )}
          </div>

          {/* 말풍선 꼬리 — 툴팁 left 65% 기준으로 왼쪽 35% 위치에 배치 */}
          <div
            style={{
              position: 'absolute',
              bottom: -5,
              left: '35%',
              marginLeft: -5,
              width: 10,
              height: 10,
              background: 'rgba(8, 8, 18, 0.90)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderTop: 'none',
              borderLeft: 'none',
              transform: 'rotate(45deg)',
            }}
          />
        </div>
      )}

      <img
        src={getSpriteSrc(agent)}
        alt={config.name}
        draggable={false}
        style={{
          width: '100%',
          height: '100%',
          userSelect: 'none',
          transform:
            agent.facingRight && (agent.state === 'walking' || agent.state === 'standing_wait')
              ? 'scaleX(-1)'
              : undefined,
          filter: isHovered ? 'brightness(1.15)' : undefined,
          transition: 'filter 0.15s ease',
        }}
      />
    </div>
  )
}
