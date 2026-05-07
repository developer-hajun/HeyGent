export const SUB_AGENT_ADAPTER_OPTIONS = [
  {
    id: 'claude_local',
    label: 'Claude Code',
    description: '로컬 Claude 에이전트',
    recommended: true,
  },
  { id: 'codex_local', label: 'Codex', description: '로컬 Codex 에이전트', recommended: true },
  { id: 'cursor', label: 'Cursor', description: '로컬 Cursor 에이전트' },
  { id: 'gemini_local', label: 'Gemini CLI', description: '로컬 Gemini 에이전트' },
  { id: 'hermes_local', label: 'Hermes Agent', description: '로컬 Hermes CLI 에이전트' },
  {
    id: 'openclaw_gateway',
    label: 'OpenClaw Gateway',
    description: '게이트웨이 프로토콜로 OpenClaw 호출',
    comingSoon: true,
  },
  { id: 'opencode_local', label: 'OpenCode', description: '로컬 멀티 제공자 에이전트' },
  { id: 'pi_local', label: 'Pi', description: '로컬 Pi 에이전트' },
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
  if (adapterType === 'cursor') return 'cursor'
  if (adapterType === 'gemini_local') return 'gemini'
  if (adapterType === 'hermes_local') return 'hermes'
  if (adapterType === 'pi_local') return 'pi'
  if (adapterType === 'opencode_local') return 'opencode'
  return 'claude'
}

export function getDefaultModel(adapterType: SubAgentAdapterType) {
  if (adapterType === 'codex_local') return 'gpt-5.4'
  if (adapterType === 'cursor') return 'claude-sonnet-4.5'
  if (adapterType === 'gemini_local') return 'gemini-2.5-pro'
  if (adapterType === 'hermes_local') return 'claude-sonnet-4.5'
  if (adapterType === 'pi_local') return 'pi-default'
  if (adapterType === 'opencode_local') return 'anthropic/claude-sonnet-4.5'
  return 'claude-sonnet-4.5'
}
