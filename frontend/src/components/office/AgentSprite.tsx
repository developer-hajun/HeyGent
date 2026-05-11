import { useState } from 'react'
import type { AgentRuntime } from './types'
import type { AgentVisualizationInfo } from './types'

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
  if (agent.state in SITTING_SPRITES) return `${base}/${SITTING_SPRITES[agent.state]}.png`
  if (agent.state === 'walking') return `${base}/${WALK_FRAMES[agent.walkFrame]}.png`
  return `${base}/idle_front.png`
}

interface AgentSpriteProps {
  agent: AgentRuntime
  onArrived: (agentId: string) => void
  onClick?: (agentId: string) => void
  hoverInfo?: AgentVisualizationInfo
  isSelected?: boolean
}

export function AgentSprite({
  agent,
  onArrived,
  onClick,
  hoverInfo,
  isSelected,
}: AgentSpriteProps) {
  const [isHovered, setIsHovered] = useState(false)
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
                  marginBottom: 8,
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

            {/* 작업 내역 */}
            {hoverInfo.taskHistory.length > 0 && (
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 8 }}>
                <div
                  style={{
                    color: 'rgba(255,255,255,0.35)',
                    fontSize: 10,
                    marginBottom: 6,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  작업 내역
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {hoverInfo.taskHistory.slice(0, 3).map((task) => (
                    <div
                      key={task.taskId}
                      style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}
                    >
                      <span style={{ color: '#86efac', fontSize: 11, flexShrink: 0 }}>✓</span>
                      <span
                        style={{ color: 'rgba(255,255,255,0.65)', fontSize: 11, lineHeight: 1.4 }}
                      >
                        {task.title}
                      </span>
                    </div>
                  ))}
                  {hoverInfo.taskHistory.length > 3 && (
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, marginTop: 2 }}>
                      +{hoverInfo.taskHistory.length - 3}개 더보기
                    </div>
                  )}
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
          filter: isSelected
            ? 'drop-shadow(0 0 10px rgba(99, 179, 237, 0.9)) brightness(1.08)'
            : isHovered
              ? 'brightness(1.15)'
              : undefined,
          transition: 'filter 0.15s ease',
        }}
      />
    </div>
  )
}
