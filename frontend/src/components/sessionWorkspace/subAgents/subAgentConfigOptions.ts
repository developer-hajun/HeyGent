export const SUB_AGENT_ADAPTER_OPTIONS = [
  {
    id: 'claude_local',
    label: 'Claude Code',
    description: '로컬 Claude 에이전트',
    recommended: true,
  },
  { id: 'codex_local', label: 'Codex', description: '로컬 Codex 에이전트', recommended: true },
] as const

export type SubAgentAdapterType = (typeof SUB_AGENT_ADAPTER_OPTIONS)[number]['id']

export function normalizeSubAgentAdapterType(value: string | undefined): SubAgentAdapterType {
  if (SUB_AGENT_ADAPTER_OPTIONS.some((option) => option.id === value)) {
    return value as SubAgentAdapterType
  }
  return 'claude_local'
}

export function getDefaultCommand(adapterType: SubAgentAdapterType) {
  if (adapterType === 'codex_local') return 'codex'
  return 'claude'
}

export function getDefaultModel(adapterType: SubAgentAdapterType) {
  if (adapterType === 'codex_local') return 'gpt-5.4'
  return 'claude-sonnet-4.5'
}
