import type { ReactNode } from 'react'
import {
  AgentAdapterTypeDropdown,
  AgentSectionCard,
} from '@/components/sessionWorkspace/AgentDetailPanels'
import { SUB_AGENT_ADAPTER_OPTIONS, type SubAgentAdapterType } from './subAgentConfigOptions'

export function AdapterSection({
  adapterType,
  onAdapterTypeChange,
}: {
  adapterType: SubAgentAdapterType
  onAdapterTypeChange: (adapterType: SubAgentAdapterType) => void
}) {
  return (
    <AgentSectionCard title="연결 방식">
      <Field label="연결 방식">
        <AgentAdapterTypeDropdown
          value={adapterType}
          options={SUB_AGENT_ADAPTER_OPTIONS.map((option) => ({
            value: option.id,
            label: option.label,
            disabled: false,
          }))}
          onChange={(value) => onAdapterTypeChange(value as SubAgentAdapterType)}
        />
      </Field>
    </AgentSectionCard>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-1.5">
        <label className="text-muted-foreground text-xs">{label}</label>
      </div>
      {children}
    </div>
  )
}
