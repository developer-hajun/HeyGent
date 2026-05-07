import { useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, Shield } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import {
  AgentModelDropdown,
  AgentSectionCard,
} from '@/components/sessionWorkspace/AgentDetailPanels'
import type { Agent } from '@/types/agent'
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
  SUB_AGENT_PROFILE_IMAGE_OPTIONS,
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
  const [roleOpen, setRoleOpen] = useState(false)
  const [revisionsOpen, setRevisionsOpen] = useState(false)
  const profileImage = getSubAgentImageBySpriteId(spriteId).src
  const selectedSpriteIndex = Math.max(
    0,
    SUB_AGENT_PROFILE_IMAGE_OPTIONS.findIndex((option) => option.id === spriteId),
  )
  const selectedSkillIds = normalizeSubAgentSkillIds(initialAgent?.skills ?? ['notion'])
  const trimmedName = nameDraft.trim()
  const duplicateName = reservedNames.some(
    (name) => name.trim().toLowerCase() === trimmedName.toLowerCase(),
  )
  const canSave = trimmedName !== '' && !duplicateName

  const handleSave = () => {
    if (!canSave) return
    onSave({
      name: trimmedName,
      description: descriptionDraft.trim(),
      instructions: initialAgent?.instructions ?? '',
      instructionsEntryFile: initialAgent?.instructionsEntryFile ?? 'AGENTS.md',
      instructionsFiles: initialAgent?.instructionsFiles ?? {},
      instructionsMode: initialAgent?.instructionsMode ?? 'managed',
      instructionsRootPath: initialAgent?.instructionsRootPath ?? '',
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
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.82fr)]">
        <div className="space-y-4">
          <AgentSectionCard title="프로필">
            <div className="grid gap-4 sm:grid-cols-[14rem_minmax(0,1fr)]">
              <div aria-label="프로필 이미지">
                <SubAgentImageStepper
                  profileImage={profileImage}
                  selectedSpriteIndex={selectedSpriteIndex}
                  onSpriteChange={setSpriteId}
                />
              </div>
              <div className="space-y-3">
                <Field label="이름">
                  <input
                    autoFocus
                    value={nameDraft}
                    onChange={(event) => setNameDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') handleSave()
                      if (event.key === 'Escape') onCancel()
                    }}
                    className={inputClass}
                    placeholder="에이전트 이름"
                  />
                  {duplicateName && (
                    <p className="text-destructive mt-1 text-xs">
                      같은 이름의 서브 에이전트가 이미 있습니다.
                    </p>
                  )}
                </Field>
                <Field label="호칭">
                  <input
                    value={titleDraft}
                    onChange={(event) => setTitleDraft(event.target.value)}
                    className={inputClass}
                    placeholder="호칭 또는 역할"
                  />
                </Field>
              </div>
            </div>
          </AgentSectionCard>

          <AgentSectionCard title="실행 환경">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="기본 환경">
                <select className={`${inputClass} cursor-not-allowed opacity-70`} value="" disabled>
                  <option value="">회사 기본값 (로컬)</option>
                </select>
              </Field>
              <Field label="역할">
                <Popover open={roleOpen} onOpenChange={setRoleOpen}>
                  <PopoverTrigger asChild>
                    <button className={`${inputClass} flex items-center justify-between gap-2`}>
                      <span className="inline-flex items-center gap-2">
                        <Shield className="text-muted-foreground h-3.5 w-3.5" />
                        {ROLE_OPTIONS.find((role) => role.id === roleDraft)?.label ?? roleDraft}
                      </span>
                      <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
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
              </Field>
              <Field label="상위 에이전트">
                <input className={`${inputClass} opacity-70`} value="CEO" disabled readOnly />
              </Field>
            </div>
          </AgentSectionCard>

          <AgentSectionCard title="역할과 능력">
            <Field label="할 수 있는 일">
              <textarea
                value={descriptionDraft}
                onChange={(event) => setDescriptionDraft(event.target.value)}
                rows={3}
                className={`${inputClass} min-h-[72px] resize-y leading-6`}
                placeholder="이 에이전트가 할 수 있는 일을 적어주세요."
              />
            </Field>
          </AgentSectionCard>
        </div>

        <div className="space-y-4">
          <AdapterSection
            adapterType={adapterType}
            onAdapterTypeChange={(nextAdapterType) => {
              setAdapterType(nextAdapterType)
              setCommandDraft(getDefaultCommand(nextAdapterType))
              setModelDraft(getDefaultModel(nextAdapterType))
            }}
          />

          <AgentSectionCard title="모델과 권한">
            <Field label="실행 명령">
              <input
                value={commandDraft}
                onChange={(event) => setCommandDraft(event.target.value)}
                className={inputClass}
                placeholder={getDefaultCommand(adapterType)}
              />
            </Field>
            <Field label="모델">
              <AgentModelDropdown
                value={modelDraft}
                options={[getDefaultModel(adapterType), modelDraft]
                  .filter(
                    (item, index, array) => item.trim() !== '' && array.indexOf(item) === index,
                  )
                  .map((item) => ({ value: item, label: item }))}
                onChange={setModelDraft}
                allowDefault={false}
                placeholder={getDefaultModel(adapterType)}
              />
            </Field>
            <Field label="추가 인자">
              <input
                value={extraArgsDraft}
                onChange={(event) => setExtraArgsDraft(event.target.value)}
                className={inputClass}
                placeholder="예: --verbose, --foo=bar"
              />
            </Field>
          </AgentSectionCard>

          <RunPolicySection
            heartbeatEnabled={heartbeatEnabled}
            intervalSec={intervalSec}
            onHeartbeatEnabledChange={setHeartbeatEnabled}
            onIntervalSecChange={setIntervalSec}
          />

          <div className="space-y-3">
            <h3 className="text-sm font-medium">API 키</h3>
            <div className="border-border rounded-lg border p-4">
              <p className="text-muted-foreground text-sm">
                API 키는 전역 설정의 제공자 연결에서 관리합니다.
              </p>
            </div>
          </div>

          <div>
            <button
              type="button"
              className="hover:text-foreground flex items-center gap-2 text-sm font-medium transition-colors"
              onClick={() => setRevisionsOpen((open) => !open)}
            >
              {revisionsOpen ? (
                <ChevronDown className="text-muted-foreground h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
              )}
              설정 변경 기록
              <span className="text-muted-foreground text-xs font-normal">0</span>
            </button>
            {revisionsOpen && (
              <p className="text-muted-foreground mt-3 text-sm">아직 설정 변경 기록이 없습니다.</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          취소
        </Button>
        <div className="flex items-center gap-2">
          <Button type="button" size="sm" onClick={handleSave} disabled={!canSave}>
            {initialAgent ? '에이전트 저장' : '에이전트 만들기'}
          </Button>
        </div>
      </div>
    </div>
  )
}

const inputClass =
  'border-border placeholder:text-muted-foreground/40 focus-visible:ring-ring w-full rounded-md border bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-muted-foreground text-xs">{label}</span>
      {children}
    </label>
  )
}

function SubAgentImageStepper({
  onSpriteChange,
  profileImage,
  selectedSpriteIndex,
}: {
  onSpriteChange: (spriteId: SubAgentSpriteId) => void
  profileImage: string
  selectedSpriteIndex: number
}) {
  return (
    <div
      className="flex min-h-36 w-full min-w-0 items-center justify-center gap-5 rounded-lg"
      aria-label="에이전트 이미지"
    >
      <button
        type="button"
        onClick={() => {
          const nextIndex =
            (selectedSpriteIndex - 1 + SUB_AGENT_PROFILE_IMAGE_OPTIONS.length) %
            SUB_AGENT_PROFILE_IMAGE_OPTIONS.length
          onSpriteChange(SUB_AGENT_PROFILE_IMAGE_OPTIONS[nextIndex].id)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="이전 에이전트 이미지"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedSpriteIndex + 1) % SUB_AGENT_PROFILE_IMAGE_OPTIONS.length
          onSpriteChange(SUB_AGENT_PROFILE_IMAGE_OPTIONS[nextIndex].id)
        }}
        className="bg-accent hover:bg-accent/80 flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
        aria-label="에이전트 이미지 변경"
      >
        <img src={profileImage} alt="" className="h-24 w-24 object-contain" draggable={false} />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedSpriteIndex + 1) % SUB_AGENT_PROFILE_IMAGE_OPTIONS.length
          onSpriteChange(SUB_AGENT_PROFILE_IMAGE_OPTIONS[nextIndex].id)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="다음 에이전트 이미지"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}
