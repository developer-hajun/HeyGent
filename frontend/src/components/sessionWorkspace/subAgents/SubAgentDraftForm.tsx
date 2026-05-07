import { useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronDown, Shield, Users } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import type { Agent } from '@/types/agent'
import { SubAgentProfileImage } from './SubAgentProfileImage'
import { SubAgentProfilePicker } from './SubAgentProfilePicker'
import { SubAgentSkillPicker } from './SubAgentSkillPicker'
import { AdapterSection, RunPolicySection } from './SubAgentConfigSections'
import {
  getDefaultCommand,
  getDefaultModel,
  normalizeSubAgentAdapterType,
  type SubAgentAdapterType,
} from './subAgentConfigOptions'
import {
  defaultSubAgentIcon,
  getSubAgentImageBySpriteId,
  normalizeSubAgentSkillIds,
  normalizeSubAgentSpriteId,
  SUB_AGENT_SKILLS,
  type SubAgentSkillId,
  type SubAgentSpriteId,
} from './subAgentOptions'

const ROLE_OPTIONS = [
  { id: 'general', label: 'General' },
  { id: 'research', label: 'Research' },
  { id: 'engineering', label: 'Engineering' },
  { id: 'qa', label: 'QA' },
] as const

export function SubAgentDraftForm({
  initialAgent,
  initialAdapterType,
  onCancel,
  onSave,
  reservedNames,
}: {
  initialAgent?: Agent
  initialAdapterType?: SubAgentAdapterType
  onCancel: () => void
  onSave: (agent: Agent) => void
  reservedNames: string[]
}) {
  const [nameDraft, setNameDraft] = useState(initialAgent?.name ?? '')
  const [titleDraft, setTitleDraft] = useState(initialAgent?.title ?? initialAgent?.role ?? '')
  const [roleDraft, setRoleDraft] = useState(initialAgent?.role ?? 'general')
  const [descriptionDraft, setDescriptionDraft] = useState(initialAgent?.description ?? '')
  const [adapterType, setAdapterType] = useState<SubAgentAdapterType>(
    normalizeSubAgentAdapterType(initialAgent?.adapterType ?? initialAdapterType),
  )
  const [commandDraft, setCommandDraft] = useState(
    initialAgent?.command ?? getDefaultCommand(adapterType),
  )
  const [modelDraft, setModelDraft] = useState(initialAgent?.model ?? getDefaultModel(adapterType))
  const [extraArgsDraft, setExtraArgsDraft] = useState(initialAgent?.extraArgs ?? '')
  const [heartbeatEnabled, setHeartbeatEnabled] = useState(initialAgent?.heartbeatEnabled ?? false)
  const [intervalSec, setIntervalSec] = useState(initialAgent?.intervalSec ?? 300)
  const [spriteId, setSpriteId] = useState<SubAgentSpriteId>(
    normalizeSubAgentSpriteId(initialAgent?.spriteId),
  )
  const [profileOpen, setProfileOpen] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const [reportsToOpen, setReportsToOpen] = useState(false)
  const profileImage = getSubAgentImageBySpriteId(spriteId).src
  const [selectedSkillIds, setSelectedSkillIds] = useState<SubAgentSkillId[]>(
    normalizeSubAgentSkillIds(initialAgent?.skills ?? ['notion']),
  )
  const selectedSkills = selectedSkillIds
    .map((skillId) => SUB_AGENT_SKILLS.find((skill) => skill.id === skillId))
    .filter((skill): skill is (typeof SUB_AGENT_SKILLS)[number] => skill !== undefined)
  const trimmedName = nameDraft.trim()
  const duplicateName = reservedNames.some(
    (name) => name.trim().toLowerCase() === trimmedName.toLowerCase(),
  )
  const canSave = trimmedName !== '' && !duplicateName

  const adoptSkill = (skillId: SubAgentSkillId) => {
    setSelectedSkillIds((current) => (current.includes(skillId) ? current : [...current, skillId]))
  }

  const removeSkill = (skillId: SubAgentSkillId) => {
    setSelectedSkillIds((current) => current.filter((id) => id !== skillId))
  }

  const handleSave = () => {
    if (!canSave) return
    onSave({
      name: trimmedName,
      description: descriptionDraft.trim(),
      icon: initialAgent?.icon ?? defaultSubAgentIcon(),
      accent: initialAgent?.accent ?? '#111827',
      title: titleDraft.trim(),
      role: roleDraft,
      adapterType,
      command: commandDraft.trim(),
      model: modelDraft.trim(),
      extraArgs: extraArgsDraft.trim(),
      heartbeatEnabled,
      intervalSec,
      profileImage,
      spriteId,
      reportsToAgentId: initialAgent?.reportsToAgentId ?? 'main',
      skills: selectedSkillIds,
    })
  }

  return (
    <div className="border-border border">
      <div className="px-4 pt-4 pb-2">
        <input
          autoFocus
          value={nameDraft}
          onChange={(event) => setNameDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') handleSave()
            if (event.key === 'Escape') onCancel()
          }}
          className="placeholder:text-muted-foreground/50 w-full bg-transparent text-lg font-semibold outline-none"
          placeholder="Agent name"
        />
        {duplicateName && (
          <p className="text-destructive mt-1 text-xs">
            같은 이름의 서브 에이전트가 이미 있습니다.
          </p>
        )}
      </div>

      <div className="px-4 pb-2">
        <input
          value={titleDraft}
          onChange={(event) => setTitleDraft(event.target.value)}
          className="text-muted-foreground placeholder:text-muted-foreground/40 w-full bg-transparent text-sm outline-none"
          placeholder="Title (e.g. VP of Engineering)"
        />
      </div>

      <div className="border-border flex flex-wrap items-center gap-1.5 border-t px-4 py-2">
        <Popover open={profileOpen} onOpenChange={setProfileOpen}>
          <PopoverTrigger asChild>
            <button className="border-border hover:bg-accent/50 inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors">
              <SubAgentProfileImage accent="#111827" profileImage={profileImage} size="compact" />
              Profile image
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-3" align="start">
            <SubAgentProfilePicker
              value={spriteId}
              onChange={(nextSpriteId) => {
                setSpriteId(nextSpriteId)
                setProfileOpen(false)
              }}
            />
          </PopoverContent>
        </Popover>

        <Popover open={roleOpen} onOpenChange={setRoleOpen}>
          <PopoverTrigger asChild>
            <button className="border-border hover:bg-accent/50 inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors">
              <Shield className="text-muted-foreground h-3 w-3" />
              {ROLE_OPTIONS.find((role) => role.id === roleDraft)?.label ?? roleDraft}
              <ChevronDown className="text-muted-foreground h-3 w-3" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-36 p-1" align="start">
            {ROLE_OPTIONS.map((role) => (
              <button
                key={role.id}
                type="button"
                className={`hover:bg-accent/50 flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs ${
                  role.id === roleDraft ? 'bg-accent' : ''
                }`}
                onClick={() => {
                  setRoleDraft(role.id)
                  setRoleOpen(false)
                }}
              >
                {role.label}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        <Popover open={reportsToOpen} onOpenChange={setReportsToOpen}>
          <PopoverTrigger asChild>
            <button className="border-border hover:bg-accent/50 inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors">
              <Users className="text-muted-foreground h-3 w-3" />
              Reports to CEO
              <ChevronDown className="text-muted-foreground h-3 w-3" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-44 p-1" align="start">
            <button
              type="button"
              className="bg-accent flex w-full items-center justify-between rounded px-2 py-1.5 text-xs"
              onClick={() => setReportsToOpen(false)}
            >
              CEO
            </button>
          </PopoverContent>
        </Popover>
      </div>

      <div className="border-border border-t px-4 py-4">
        <div className="space-y-3">
          <Field label="Capabilities">
            <textarea
              value={descriptionDraft}
              onChange={(event) => setDescriptionDraft(event.target.value)}
              rows={3}
              className="border-border placeholder:text-muted-foreground/40 min-h-[60px] w-full resize-none rounded-md border bg-transparent px-2.5 py-1.5 font-mono text-sm outline-none"
              placeholder="Describe what this agent can do."
            />
          </Field>
        </div>
      </div>

      <AdapterSection
        adapterType={adapterType}
        command={commandDraft}
        extraArgs={extraArgsDraft}
        model={modelDraft}
        onAdapterTypeChange={(nextAdapterType) => {
          setAdapterType(nextAdapterType)
          setCommandDraft(getDefaultCommand(nextAdapterType))
          setModelDraft(getDefaultModel(nextAdapterType))
        }}
        onCommandChange={setCommandDraft}
        onExtraArgsChange={setExtraArgsDraft}
        onModelChange={setModelDraft}
      />

      <RunPolicySection
        heartbeatEnabled={heartbeatEnabled}
        intervalSec={intervalSec}
        onHeartbeatEnabledChange={setHeartbeatEnabled}
        onIntervalSecChange={setIntervalSec}
      />

      <SubAgentSkillPicker
        onAdoptSkill={adoptSkill}
        onRemoveSkill={removeSkill}
        selectedSkills={selectedSkills}
      />

      <div className="border-border border-t px-4 py-3">
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <Button type="button" variant="outline" size="sm" onClick={onCancel}>
              Cancel
            </Button>
            <div className="flex items-center gap-2">
              <Button type="button" size="sm" onClick={handleSave} disabled={!canSave}>
                {initialAgent ? 'Save agent' : 'Create agent'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-muted-foreground text-xs">{label}</span>
      {children}
    </label>
  )
}
