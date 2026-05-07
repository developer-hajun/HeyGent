import { useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronDown, Heart } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  getDefaultCommand,
  getDefaultModel,
  SUB_AGENT_ADAPTER_OPTIONS,
  type SubAgentAdapterType,
} from './subAgentConfigOptions'

export function AdapterSection({
  adapterType,
  command,
  extraArgs,
  model,
  onAdapterTypeChange,
  onCommandChange,
  onExtraArgsChange,
  onModelChange,
}: {
  adapterType: SubAgentAdapterType
  command: string
  extraArgs: string
  model: string
  onAdapterTypeChange: (adapterType: SubAgentAdapterType) => void
  onCommandChange: (value: string) => void
  onExtraArgsChange: (value: string) => void
  onModelChange: (value: string) => void
}) {
  const [adapterOpen, setAdapterOpen] = useState(false)
  const selectedAdapter = SUB_AGENT_ADAPTER_OPTIONS.find((option) => option.id === adapterType)

  return (
    <>
      <div className="border-border border-t">
        <div className="flex items-center justify-between gap-2 px-4 py-2">
          <span className="text-muted-foreground text-xs font-medium">Adapter</span>
        </div>
        <div className="space-y-3 px-4 pb-3">
          <Field label="Adapter type">
            <Popover open={adapterOpen} onOpenChange={setAdapterOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="border-border hover:bg-accent/50 inline-flex w-full items-center justify-between gap-1.5 rounded-md border px-2.5 py-1.5 text-sm transition-colors"
                >
                  <span className="truncate">{selectedAdapter?.label ?? adapterType}</span>
                  <ChevronDown className="text-muted-foreground h-3 w-3" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-1" align="start">
                {SUB_AGENT_ADAPTER_OPTIONS.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    className={`hover:bg-accent/50 flex w-full items-center justify-between rounded px-2 py-1.5 text-sm ${
                      option.id === adapterType ? 'bg-accent' : ''
                    } ${'comingSoon' in option && option.comingSoon ? 'cursor-not-allowed opacity-40' : ''}`}
                    disabled={'comingSoon' in option && option.comingSoon}
                    title={'comingSoon' in option && option.comingSoon ? 'Coming soon' : undefined}
                    onClick={() => {
                      if ('comingSoon' in option && option.comingSoon) return
                      onAdapterTypeChange(option.id)
                      setAdapterOpen(false)
                    }}
                  >
                    <span>{option.label}</span>
                  </button>
                ))}
              </PopoverContent>
            </Popover>
          </Field>
        </div>
      </div>

      <div className="border-border border-b">
        <div className="text-muted-foreground px-4 py-2 text-xs font-medium">
          Permissions &amp; Configuration
        </div>
        <div className="space-y-3 px-4 pb-3">
          <Field label="Command">
            <input
              value={command}
              onChange={(event) => onCommandChange(event.target.value)}
              className={inputClass}
              placeholder={getDefaultCommand(adapterType)}
            />
          </Field>
          <Field label="Model">
            <input
              value={model}
              onChange={(event) => onModelChange(event.target.value)}
              className={inputClass}
              placeholder={getDefaultModel(adapterType)}
            />
          </Field>
          <Field label="Extra args (comma-separated)">
            <input
              value={extraArgs}
              onChange={(event) => onExtraArgsChange(event.target.value)}
              className={inputClass}
              placeholder="e.g. --verbose, --foo=bar"
            />
          </Field>
        </div>
      </div>
    </>
  )
}

export function RunPolicySection({
  heartbeatEnabled,
  intervalSec,
  onHeartbeatEnabledChange,
  onIntervalSecChange,
}: {
  heartbeatEnabled: boolean
  intervalSec: number
  onHeartbeatEnabledChange: (value: boolean) => void
  onIntervalSecChange: (value: number) => void
}) {
  return (
    <div className="border-border border-b">
      <div className="text-muted-foreground flex items-center gap-2 px-4 py-2 text-xs font-medium">
        <Heart className="h-3 w-3" />
        Run Policy
      </div>
      <div className="space-y-3 px-4 pb-3">
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground text-xs">Heartbeat on interval</span>
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
          {heartbeatEnabled && (
            <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <span>Run heartbeat every</span>
              <input
                type="number"
                className="border-border w-16 rounded-md border bg-transparent px-2 py-0.5 text-center font-mono text-xs outline-none"
                value={intervalSec}
                onChange={(event) => onIntervalSecChange(Number(event.target.value) || 0)}
              />
              <span>sec</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

const inputClass =
  'w-full rounded-md border border-border px-2.5 py-1.5 bg-transparent outline-none text-sm font-mono placeholder:text-muted-foreground/40'

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
