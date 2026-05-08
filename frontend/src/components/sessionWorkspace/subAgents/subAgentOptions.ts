import { Bot, Code2, Dumbbell, FileText } from 'lucide-react'

export const SUB_AGENT_PROFILE_IMAGE_OPTIONS = [
  { id: 'agent01', label: 'Agent 01', src: '/assets/agents/agent01/idle_front.png' },
  { id: 'agent02', label: 'Agent 02', src: '/assets/agents/agent02/idle_front.png' },
  { id: 'agent03', label: 'Agent 03', src: '/assets/agents/agent03/idle_front.png' },
  { id: 'agent04', label: 'Agent 04', src: '/assets/agents/agent04/idle_front.png' },
  { id: 'agent05', label: 'Agent 05', src: '/assets/agents/agent05/idle_front.png' },
  { id: 'agent06', label: 'Agent 06', src: '/assets/agents/agent06/idle_front.png' },
  { id: 'agent07', label: 'Agent 07', src: '/assets/agents/agent07/idle_front.png' },
  { id: 'agent08', label: 'Agent 08', src: '/assets/agents/agent08/idle_front.png' },
  { id: 'agent09', label: 'Agent 09', src: '/assets/agents/agent09/idle_front.png' },
  { id: 'agent10', label: 'Agent 10', src: '/assets/agents/agent10/idle_front.png' },
] as const

export type SubAgentSpriteId = (typeof SUB_AGENT_PROFILE_IMAGE_OPTIONS)[number]['id']

export const SUB_AGENT_SKILLS = [
  {
    id: 'notion',
    label: 'Notion',
    description: '문서와 데이터베이스를 정리합니다.',
    icon: FileText,
  },
  {
    id: 'samsung-health',
    label: 'Samsung Health',
    description: '건강 기록과 루틴 맥락을 확인합니다.',
    icon: Dumbbell,
  },
  {
    id: 'code',
    label: 'Code',
    description: '코드 읽기와 구현 작업을 맡습니다.',
    icon: Code2,
  },
] as const

export type SubAgentSkillId = (typeof SUB_AGENT_SKILLS)[number]['id']
export type SubAgentSkillOption = (typeof SUB_AGENT_SKILLS)[number]

export function normalizeSubAgentProfileImage(value: string | undefined) {
  if (
    value !== undefined &&
    SUB_AGENT_PROFILE_IMAGE_OPTIONS.some((option) => option.src === value)
  ) {
    return value
  }
  return SUB_AGENT_PROFILE_IMAGE_OPTIONS[0].src
}

export function normalizeSubAgentSpriteId(value: string | undefined): SubAgentSpriteId {
  if (
    value !== undefined &&
    SUB_AGENT_PROFILE_IMAGE_OPTIONS.some((option) => option.id === value)
  ) {
    return value as SubAgentSpriteId
  }
  return SUB_AGENT_PROFILE_IMAGE_OPTIONS[0].id
}

export function getSubAgentImageBySpriteId(spriteId: string | undefined) {
  const normalized = normalizeSubAgentSpriteId(spriteId)
  return (
    SUB_AGENT_PROFILE_IMAGE_OPTIONS.find((option) => option.id === normalized) ??
    SUB_AGENT_PROFILE_IMAGE_OPTIONS[0]
  )
}

export function normalizeSubAgentSkillIds(values: string[] | undefined): SubAgentSkillId[] {
  if (!Array.isArray(values)) return []
  return values.filter((value): value is SubAgentSkillId =>
    SUB_AGENT_SKILLS.some((skill) => skill.id === value),
  )
}

export function defaultSubAgentIcon() {
  return Bot
}
