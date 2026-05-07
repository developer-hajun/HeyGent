import { useState } from 'react'
import { Activity, BarChart3, Clock, FileText, MoreHorizontal, Play, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageTabBar } from '@/components/PageTabBar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tabs } from '@/components/ui/tabs'
import type { AgentPanelItem } from '@/store/useSessionStore'
import type { Agent } from '@/types/agent'
import { SubAgentDraftForm } from './SubAgentDraftForm'
import { SubAgentProfileImage } from './SubAgentProfileImage'
import { SUB_AGENT_SKILLS } from './subAgentOptions'

type SubAgentDetailTab =
  | 'dashboard'
  | 'instructions'
  | 'skills'
  | 'configuration'
  | 'runs'
  | 'budget'

const DETAIL_TABS: Array<{ value: SubAgentDetailTab; label: string }> = [
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'instructions', label: 'Instructions' },
  { value: 'skills', label: 'Skills' },
  { value: 'configuration', label: 'Configuration' },
  { value: 'runs', label: 'Runs' },
  { value: 'budget', label: 'Budget' },
]

export function SubAgentDetailView({
  item,
  onSave,
  reservedNames,
  requestedTab,
}: {
  item: AgentPanelItem
  onSave: (agent: Agent) => void
  requestedTab?: string | null
  reservedNames: string[]
}) {
  const [tab, setTab] = useState<SubAgentDetailTab>(getDetailTab(requestedTab))
  const selectedSkills = SUB_AGENT_SKILLS.filter((skill) => item.agent.skills?.includes(skill.id))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-3">
          <SubAgentProfileImage
            accent={item.agent.accent}
            profileImage={item.agent.profileImage}
            spriteId={item.agent.spriteId}
            size="large"
          />
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-bold">{item.agent.name}</h1>
            <p className="text-muted-foreground truncate text-sm">
              {item.agent.role ?? 'general'}
              {item.agent.title ? ` - ${item.agent.title}` : ''}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <Button variant="outline" size="sm" onClick={() => setTab('configuration')}>
            <FileText className="h-3.5 w-3.5 sm:mr-1" />
            <span className="hidden sm:inline">Configuration</span>
          </Button>
          <Button variant="outline" size="sm" onClick={() => setTab('runs')}>
            <Play className="h-3.5 w-3.5 sm:mr-1" />
            <span className="hidden sm:inline">Runs</span>
          </Button>
          <span className="border-border bg-muted/40 hidden rounded-full border px-2 py-0.5 text-xs sm:inline">
            draft
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                aria-label={`${item.agent.name} actions`}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem onClick={() => setTab('configuration')}>
                <Settings className="size-4" />
                <span>Configuration</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <Tabs value={tab} onValueChange={(next) => setTab(next as SubAgentDetailTab)}>
        <PageTabBar
          items={DETAIL_TABS}
          value={tab}
          onValueChange={(next) => setTab(next as SubAgentDetailTab)}
        />
      </Tabs>

      {tab === 'dashboard' && (
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricCard icon={Activity} label="Status" value="Draft" />
          <MetricCard icon={BarChart3} label="Skills" value={String(selectedSkills.length)} />
          <MetricCard icon={Clock} label="Runs" value="0" />
        </div>
      )}

      {tab === 'configuration' && (
        <div className="max-w-3xl">
          <SubAgentDraftForm
            key={item.id}
            initialAgent={item.agent}
            onCancel={() => setTab('dashboard')}
            onSave={onSave}
            reservedNames={reservedNames}
          />
        </div>
      )}

      {tab === 'instructions' && (
        <div className="max-w-3xl space-y-4">
          <section className="space-y-3">
            <h3 className="text-sm font-medium">Instructions</h3>
            <div className="border-border bg-background rounded-lg border p-4">
              <p className="text-sm leading-6 whitespace-pre-wrap">
                {item.agent.description || 'No instructions configured yet.'}
              </p>
            </div>
          </section>
        </div>
      )}

      {tab === 'skills' && (
        <section className="border-border border">
          {selectedSkills.length === 0 ? (
            <p className="text-muted-foreground px-4 py-3 text-sm">No optional skills selected.</p>
          ) : (
            selectedSkills.map((skill) => (
              <Row key={skill.id} label={skill.label} value={skill.description} />
            ))
          )}
        </section>
      )}

      {tab === 'runs' && (
        <section className="border-border text-muted-foreground border px-4 py-6 text-sm">
          No runs yet.
        </section>
      )}

      {tab === 'budget' && (
        <div className="max-w-3xl">
          <section className="space-y-3">
            <h3 className="text-sm font-medium">Budget</h3>
            <div className="border-border bg-background text-muted-foreground rounded-lg border p-4 text-sm">
              No budget policy configured.
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function getDetailTab(value: string | null | undefined): SubAgentDetailTab {
  return DETAIL_TABS.some((tab) => tab.value === value) ? (value as SubAgentDetailTab) : 'dashboard'
}

function MetricCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Activity
  label: string
  value: string
}) {
  return (
    <div className="border-border rounded-lg border p-4">
      <div className="text-muted-foreground flex items-center gap-2 text-xs">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-2 text-lg font-semibold">{value}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-border flex items-center justify-between gap-4 border-b px-4 py-2.5 last:border-b-0">
      <span className="text-sm font-medium">{label}</span>
      <span className="text-muted-foreground min-w-0 truncate text-sm">{value || '-'}</span>
    </div>
  )
}
