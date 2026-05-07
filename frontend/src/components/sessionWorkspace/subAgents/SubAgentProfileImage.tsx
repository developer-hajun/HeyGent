import { getSubAgentImageBySpriteId, normalizeSubAgentProfileImage } from './subAgentOptions'

export function SubAgentProfileImage({
  accent,
  profileImage,
  size = 'default',
  spriteId,
}: {
  accent: string
  profileImage?: string
  size?: 'compact' | 'default' | 'large'
  spriteId?: string
}) {
  const image = profileImage ?? getSubAgentImageBySpriteId(spriteId).src
  const shellClass =
    size === 'compact'
      ? 'flex h-4 w-4 shrink-0 items-center justify-center overflow-hidden rounded bg-accent'
      : size === 'large'
        ? 'bg-accent flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors'
        : 'bg-accent border-border flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg border'
  const imageClass =
    size === 'compact'
      ? 'h-4 w-4 object-contain'
      : size === 'large'
        ? 'h-10 w-10 object-contain'
        : 'h-8 w-8 object-contain'

  return (
    <span className={shellClass} style={{ borderColor: accent }}>
      <img
        src={normalizeSubAgentProfileImage(image)}
        alt=""
        className={imageClass}
        draggable={false}
      />
    </span>
  )
}
