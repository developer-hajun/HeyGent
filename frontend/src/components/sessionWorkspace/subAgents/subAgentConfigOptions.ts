export const SUB_AGENT_ADAPTER_OPTIONS = [
  {
    id: 'claude_local',
    label: 'Claude Code',
    description: 'Local Claude agent',
    recommended: true,
  },
  { id: 'codex_local', label: 'Codex', description: 'Local Codex agent', recommended: true },
  { id: 'cursor', label: 'Cursor', description: 'Local Cursor agent' },
  { id: 'gemini_local', label: 'Gemini CLI', description: 'Local Gemini agent' },
  { id: 'hermes_local', label: 'Hermes Agent', description: 'Local Hermes CLI agent' },
  {
    id: 'openclaw_gateway',
    label: 'OpenClaw Gateway',
    description: 'Invoke OpenClaw via gateway protocol',
    comingSoon: true,
  },
  { id: 'opencode_local', label: 'OpenCode', description: 'Local multi-provider agent' },
  { id: 'pi_local', label: 'Pi', description: 'Local Pi agent' },
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
