export const SUB_AGENT_ADAPTER_OPTIONS = [
  {
    id: 'openai',
    label: 'OpenAI',
    description: 'OpenAI API 키로 실행',
    recommended: true,
  },
] as const

export type SubAgentAdapterType = (typeof SUB_AGENT_ADAPTER_OPTIONS)[number]['id']

export function normalizeSubAgentAdapterType(value: string | undefined): SubAgentAdapterType {
  if (SUB_AGENT_ADAPTER_OPTIONS.some((option) => option.id === value)) {
    return value as SubAgentAdapterType
  }
  return 'openai'
}

export function getDefaultModel() {
  return 'gpt-5.4'
}
