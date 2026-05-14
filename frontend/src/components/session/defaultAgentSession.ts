import type { CustomAgentConfig } from './NewSessionModal'

export const CEO_IMAGE_OPTIONS = [
  { id: 'desk', label: '책상', src: '/assets/agents/ceo/ceo_desk.png' },
  { id: 'explain', label: '설명', src: '/assets/agents/ceo/ceo_explain.png' },
  { id: 'profile', label: '프로필', src: '/assets/agents/ceo/ceo_profile.png' },
] as const

export function defaultAgentSessionConfig(): CustomAgentConfig {
  return {
    seedDefaultAgents: true,
    agentName: '팀장 에이전트',
    persona: '',
    callName: '팀장 에이전트',
    capabilities: '',
    profileImage: CEO_IMAGE_OPTIONS[0].src,
    model: 'gpt-5.4',
    delegationPolicy: { canDelegate: true },
    instructionsEntryFile: 'AGENTS.md',
    instructionsMode: 'managed',
    instructionsRootPath: '',
    instructionsFiles: {},
  }
}
