import type { ReactNode } from 'react'
import { Heart } from 'lucide-react'
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

export function RunPolicySection({
  heartbeatEnabled,
  onHeartbeatEnabledChange,
}: {
  heartbeatEnabled: boolean
  onHeartbeatEnabledChange: (value: boolean) => void
}) {
  return (
    <AgentSectionCard title="실행 규칙">
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            <Heart className="text-muted-foreground h-3 w-3" />
            <span className="text-muted-foreground text-xs">정해진 주기로 실행</span>
          </div>
          <button
            type="button"
            data-slot="toggle"
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
              heartbeatEnabled ? 'bg-green-600' : 'bg-muted'
            }`}
            onClick={() => onHeartbeatEnabledChange(!heartbeatEnabled)}
          >
            <span
              className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                heartbeatEnabled ? 'translate-x-4.5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>
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
