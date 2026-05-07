import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import {
  Bot,
  Check,
  ChevronLeft,
  ChevronRight,
  Code2,
  Dumbbell,
  FileText,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  Save,
  Search,
  Trash2,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { AgentStatusPage } from '@/pages/AgentStatusPage'
import { useChatStore } from '@/store/useChatStore'
import { useSessionStore } from '@/store/useSessionStore'
import type { JsonObject } from '@/realtime/aiRealtimeTypes'
import type { AiModelOption, AiSessionSettingsPatch, RawAiSession } from '@/types/aiChat'
import type { Agent } from '@/types/agent'
import {
  getModelFamilies,
  getModelOptions,
  getString,
  groupModels,
  inferModelFamily,
  setOptionalUiString,
  shallowJsonEqual,
  toJsonObject,
} from './sessionWorkspaceUtils'
import type { ModelFamily } from './sessionWorkspaceUtils'
import type { WorkspacePanelId } from './sessionWorkspaceTypes'

interface SessionWorkspaceDetailPanelProps {
  activePanel: WorkspacePanelId | null
  sessionId: string
  session: RawAiSession | null
}

export function SessionWorkspaceDetailPanel({
  activePanel,
  sessionId,
  session,
}: SessionWorkspaceDetailPanelProps) {
  if (activePanel === null) {
    return null
  }

  if (activePanel === 'subAgents') {
    return <SubAgentsPage sessionId={sessionId} />
  }

  if (activePanel === 'visualization') {
    return <AgentStatusPage />
  }

  if (session === null) {
    const title = activePanel === 'purpose' ? '메인 에이전트' : '세션'
    return (
      <WorkspacePageShell title={title} eyebrow="작업면">
        <p className="text-muted-foreground text-sm">세션 정보를 불러오는 중입니다.</p>
      </WorkspacePageShell>
    )
  }

  if (activePanel === 'purpose') {
    return <PurposePage session={session} />
  }

  return null
}

function PurposePage({ session }: { session: RawAiSession }) {
  const updateSession = useChatStore((state) => state.updateSession)
  const updateSessionSettings = useChatStore((state) => state.updateSessionSettings)
  const fetchModelOptions = useChatStore((state) => state.fetchModelOptions)

  const metadata = useMemo(() => toJsonObject(session.metadata), [session.metadata])
  const uiMetadata = useMemo(() => toJsonObject(metadata.ui), [metadata])
  const settings = useMemo(() => toJsonObject(session.settings), [session.settings])
  const sessionId = session.session_id
  const currentPurpose = getString(uiMetadata, 'sessionPurpose') ?? ''
  const currentAgentName = getString(uiMetadata, 'agentName') ?? ''
  const currentCallName = getString(uiMetadata, 'callName') ?? ''
  const currentPersona =
    getString(settings, 'systemPrompt') ?? getString(settings, 'system_prompt') ?? ''
  const currentSuccessCriteria = getString(uiMetadata, 'successCriteria') ?? ''
  const currentConstraints = getString(uiMetadata, 'constraints') ?? ''
  const currentModel = getString(settings, 'model') ?? ''
  const currentProfileImage =
    getString(uiMetadata, 'agentProfileImage') ?? AGENT_IMAGE_OPTIONS[0].src
  const [purpose, setPurpose] = useState(currentPurpose)
  const [agentName, setAgentName] = useState(currentAgentName)
  const [callName, setCallName] = useState(currentCallName)
  const [persona, setPersona] = useState(currentPersona)
  const [successCriteria, setSuccessCriteria] = useState(currentSuccessCriteria)
  const [constraints, setConstraints] = useState(currentConstraints)
  const [selectedModel, setSelectedModel] = useState(currentModel)
  const [profileImage, setProfileImage] = useState(currentProfileImage)
  const [modelOptionsLoading, setModelOptionsLoading] = useState(true)
  const [modelOptionsError, setModelOptionsError] = useState<string | null>(null)
  const [modelOptions, setModelOptions] = useState(getModelOptions(undefined))
  const [selectedFamily, setSelectedFamily] = useState<ModelFamily>(inferModelFamily(currentModel))
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const modelGroups = useMemo(() => groupModels(modelOptions), [modelOptions])
  const modelFamilies = useMemo(() => getModelFamilies(modelGroups), [modelGroups])
  const effectiveSelectedFamily = modelFamilies.some((family) => family.id === selectedFamily)
    ? selectedFamily
    : (modelFamilies[0]?.id ?? 'gpt')
  const visibleModels = modelGroups[effectiveSelectedFamily]
  const selectedImageIndex = Math.max(
    0,
    AGENT_IMAGE_OPTIONS.findIndex((option) => option.src === profileImage),
  )

  useEffect(() => {
    let active = true

    void fetchModelOptions(sessionId)
      .then((options) => {
        if (!active) return
        const nextModels = getModelOptions(options.models)
        setModelOptions(nextModels)
        setModelOptionsLoading(false)
        if (currentModel === '' && typeof options.model === 'string' && options.model.trim()) {
          setSelectedModel(options.model)
          setSelectedFamily(inferModelFamily(options.model))
        }
      })
      .catch((error) => {
        if (!active) return
        setModelOptionsError(
          error instanceof Error ? error.message : '모델 목록 조회에 실패했습니다.',
        )
        setModelOptionsLoading(false)
      })

    return () => {
      active = false
    }
  }, [currentModel, fetchModelOptions, sessionId])

  const markDirty = () => {
    setSaved(false)
    setSaveError(null)
  }

  const handleSave = async () => {
    const nextUiMetadata: JsonObject = { ...uiMetadata }
    setOptionalUiString(nextUiMetadata, 'sessionPurpose', purpose)
    setOptionalUiString(nextUiMetadata, 'agentName', agentName)
    setOptionalUiString(nextUiMetadata, 'callName', callName)
    setOptionalUiString(nextUiMetadata, 'successCriteria', successCriteria)
    setOptionalUiString(nextUiMetadata, 'constraints', constraints)
    setOptionalUiString(nextUiMetadata, 'agentProfileImage', profileImage)

    const settingsPatch: AiSessionSettingsPatch = {}
    const nextPersona = persona.trim()
    if (nextPersona !== currentPersona) {
      settingsPatch.systemPrompt = nextPersona
    }
    if (selectedModel !== '' && selectedModel !== currentModel) {
      settingsPatch.model = selectedModel
    }

    setSaving(true)
    setSaveError(null)
    setSaved(false)

    try {
      if (!shallowJsonEqual(uiMetadata, nextUiMetadata)) {
        await updateSession({ sessionId, metadataPatch: { ui: nextUiMetadata } })
      }
      if (Object.keys(settingsPatch).length > 0) {
        await updateSessionSettings({ sessionId, settingsPatch })
      }
      setSaved(true)
      window.setTimeout(() => setSaved(false), 1400)
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : '목표 저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <WorkspacePageShell
      title="메인 에이전트"
      eyebrow="CEO"
      action={
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="border-border hover:bg-accent/50 inline-flex items-center gap-1.5 border px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-60"
        >
          {saving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : saved ? (
            <Check className="h-3.5 w-3.5" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          {saved ? '저장됨' : '저장'}
        </button>
      }
    >
      <div className="space-y-6">
        {saveError && <p className="text-destructive text-sm">{saveError}</p>}
        <div className="space-y-3">
          <div className="text-muted-foreground text-xs">대화 프롬프트</div>
          <div className="border-border grid grid-cols-[minmax(0,4fr)_minmax(0,3fr)] overflow-hidden border">
            <div className="border-border min-w-0 border-r">
              <PromptEntityRow
                title="대화 목표"
                value={purpose}
                onChange={setPurpose}
                onDirty={markDirty}
                placeholder="예: 이번 대화에서는 3분 발표용 서비스 소개안을 완성한다."
                multiline
                rows={2}
              />
              <PromptEntityRow
                title="응답 역할"
                value={persona}
                onChange={setPersona}
                onDirty={markDirty}
                placeholder="예: PM처럼 질문하고, 근거가 부족하면 먼저 확인하며, 답변은 실행 항목 중심으로 정리한다."
                multiline
                rows={3}
              />
            </div>
            <div className="min-w-0 space-y-4 p-3 sm:p-4">
              <ModelSelector
                effectiveSelectedFamily={effectiveSelectedFamily}
                modelFamilies={modelFamilies}
                modelOptionsError={modelOptionsError}
                modelOptionsLoading={modelOptionsLoading}
                onModelSelect={(modelId) => {
                  setSelectedModel(modelId)
                  setSaved(false)
                }}
                onFamilySelect={setSelectedFamily}
                selectedModel={selectedModel}
                visibleModels={visibleModels}
              />
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-start">
            <span className="text-muted-foreground text-xs">세부사항</span>
          </div>
          <div className="border-border grid grid-cols-[minmax(170px,1fr)_minmax(0,4fr)] overflow-hidden border">
            <div className="border-border flex min-w-0 items-center justify-center border-r p-2 sm:p-3">
              <AgentImageSelector
                profileImage={profileImage}
                selectedImageIndex={selectedImageIndex}
                onProfileImageChange={(image) => {
                  setProfileImage(image)
                  setSaved(false)
                }}
              />
            </div>

            <div className="min-w-0">
              <PromptEntityRow
                identifier="이름"
                title="에이전트 이름"
                value={agentName}
                onChange={setAgentName}
                onDirty={markDirty}
                placeholder="예: 기획 도우미"
              />
              <PromptEntityRow
                identifier="호칭"
                title="호칭"
                value={callName}
                onChange={setCallName}
                onDirty={markDirty}
                placeholder="예: 팀장님, 사용자님"
              />
              <PromptEntityRow
                identifier="완료"
                title="성공 기준"
                value={successCriteria}
                onChange={setSuccessCriteria}
                onDirty={markDirty}
                placeholder="예: 최종 답변에 문제 정의, 해결안, 다음 액션 3개가 포함되어야 합니다."
                multiline
              />
              <PromptEntityRow
                identifier="제약"
                title="제약"
                value={constraints}
                onChange={setConstraints}
                onDirty={markDirty}
                placeholder="예: 추측하지 말고 모르는 내용은 확인 질문으로 남겨주세요."
                multiline
              />
            </div>
          </div>
        </div>
      </div>
    </WorkspacePageShell>
  )
}

const AGENT_IMAGE_OPTIONS = [
  { id: 'agent01', label: '팀장', src: '/assets/agents/agent01/idle_front.png' },
  { id: 'agent02', label: '분석가', src: '/assets/agents/agent02/idle_front.png' },
  { id: 'agent03', label: '기획자', src: '/assets/agents/agent03/idle_front.png' },
  { id: 'agent04', label: '개발자', src: '/assets/agents/agent04/idle_front.png' },
]

function ModelSelector({
  effectiveSelectedFamily,
  modelFamilies,
  modelOptionsError,
  modelOptionsLoading,
  onFamilySelect,
  onModelSelect,
  selectedModel,
  visibleModels,
}: {
  effectiveSelectedFamily: ModelFamily
  modelFamilies: Array<{ id: ModelFamily; label: string }>
  modelOptionsError: string | null
  modelOptionsLoading: boolean
  onFamilySelect: (family: ModelFamily) => void
  onModelSelect: (modelId: string) => void
  selectedModel: string
  visibleModels: AiModelOption[]
}) {
  return (
    <section className="space-y-3">
      <div className="text-muted-foreground text-xs">모델</div>
      <div className="border-border flex items-center gap-1 border-b">
        {modelFamilies.map((family) => (
          <button
            key={family.id}
            type="button"
            onClick={() => onFamilySelect(family.id)}
            className={`border-b px-3 py-2 text-sm font-medium transition-colors ${
              effectiveSelectedFamily === family.id
                ? 'border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground border-transparent'
            }`}
          >
            {family.label}
          </button>
        ))}
        {modelOptionsLoading && (
          <span className="text-muted-foreground ml-auto inline-flex items-center gap-1.5 text-xs">
            <Loader2 className="h-3 w-3 animate-spin" />
            조회 중
          </span>
        )}
      </div>

      {modelOptionsError && (
        <p className="text-destructive text-sm">{formatServerError(modelOptionsError)}</p>
      )}

      <div className="border-border max-h-80 overflow-y-auto border">
        {visibleModels.map((model) => (
          <button
            key={`${model.provider ?? 'model'}:${model.id}`}
            type="button"
            onClick={() => onModelSelect(model.id)}
            disabled={modelOptionsLoading || modelOptionsError !== null}
            className="border-border hover:bg-accent/50 flex w-full items-center gap-3 border-b px-4 py-2 text-left text-sm transition-colors last:border-b-0 disabled:opacity-60"
          >
            <span className="text-muted-foreground hidden w-20 shrink-0 text-xs capitalize sm:inline">
              {model.provider ?? effectiveSelectedFamily}
            </span>
            <span className="min-w-0 flex-1 truncate">{model.label}</span>
            {selectedModel === model.id && <Check className="h-4 w-4 shrink-0" />}
          </button>
        ))}
        {!modelOptionsLoading && visibleModels.length === 0 && (
          <p className="text-muted-foreground px-4 py-2 text-sm">선택 가능한 모델이 없습니다.</p>
        )}
      </div>
    </section>
  )
}

function AgentImageSelector({
  onProfileImageChange,
  profileImage,
  selectedImageIndex,
}: {
  onProfileImageChange: (image: string) => void
  profileImage: string
  selectedImageIndex: number
}) {
  const selectedImage = AGENT_IMAGE_OPTIONS[selectedImageIndex]

  return (
    <div
      className="flex w-full min-w-0 items-center justify-center gap-1 sm:gap-2"
      aria-label="에이전트 이미지"
    >
      <button
        type="button"
        onClick={() => {
          const nextIndex =
            (selectedImageIndex - 1 + AGENT_IMAGE_OPTIONS.length) % AGENT_IMAGE_OPTIONS.length
          onProfileImageChange(AGENT_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center transition-colors"
        aria-label="이전 에이전트 이미지"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <div className="bg-muted flex aspect-square w-full max-w-28 min-w-20 shrink items-end justify-center overflow-hidden">
        <img
          src={profileImage}
          alt={selectedImage?.label ?? '메인 에이전트'}
          className="h-full w-full object-contain"
          draggable={false}
        />
      </div>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % AGENT_IMAGE_OPTIONS.length
          onProfileImageChange(AGENT_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center transition-colors"
        aria-label="다음 에이전트 이미지"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}

const SUB_AGENT_SKILLS = [
  {
    id: 'notion',
    label: 'Notion',
    description: '문서와 데이터베이스를 정리합니다.',
    icon: FileText,
  },
  {
    id: 'samsung-health',
    label: 'Samsung Health',
    description: '건강 기록과 루틴 맥락을 확인합니다.',
    icon: Dumbbell,
  },
  {
    id: 'code',
    label: 'Code',
    description: '코드 읽기와 구현 작업을 맡습니다.',
    icon: Code2,
  },
] as const

type SubAgentSkillId = (typeof SUB_AGENT_SKILLS)[number]['id']

function SubAgentsPage({ sessionId }: { sessionId: string }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const {
    addAgentPanelToSession,
    getAgentPanelsForSession,
    removeAgentPanelFromSession,
    updateAgentPanelInSession,
  } = useSessionStore()
  const agentPanels = getAgentPanelsForSession(sessionId)
  const editingId = searchParams.get('edit')
  const editingItem =
    editingId === null ? undefined : agentPanels.find((panel) => panel.id === editingId)
  const draftMode =
    searchParams.get('new') === '1' ? 'create' : editingItem !== undefined ? 'edit' : null

  const resetDraft = () => {
    setSearchParams({})
  }

  const openEditDraft = (itemId: string) => {
    setSearchParams({ edit: itemId })
  }

  return (
    <WorkspacePageShell title="에이전트" eyebrow="에이전트">
      <div className="space-y-4">
        {draftMode !== null && (
          <SubAgentDraftForm
            key={draftMode === 'edit' ? editingItem?.id : 'create'}
            initialAgent={draftMode === 'edit' ? editingItem?.agent : undefined}
            onCancel={resetDraft}
            onSave={(agent) => {
              if (draftMode === 'edit') {
                if (editingItem === undefined) return
                updateAgentPanelInSession(sessionId, editingItem.id, agent)
              } else {
                addAgentPanelToSession(sessionId, agent)
              }
              resetDraft()
            }}
          />
        )}

        <div className="border-border border">
          {agentPanels.length === 0 ? (
            <p className="text-muted-foreground px-4 py-2 text-sm">
              에이전트가 없습니다. 사이드바의 + 버튼으로 역할을 나눌 수 있습니다.
            </p>
          ) : (
            agentPanels.map((item) => (
              <div
                key={item.id}
                className="group/agent border-border hover:bg-accent/50 flex items-center gap-3 border-b px-4 py-2 text-sm transition-colors last:border-b-0"
              >
                <button
                  type="button"
                  onClick={() => openEditDraft(item.id)}
                  className="flex min-w-0 flex-1 items-center gap-3 text-left"
                >
                  <item.agent.icon
                    className="h-4 w-4 shrink-0"
                    style={{ color: item.agent.accent }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate">{item.agent.name}</span>
                    {item.agent.description && (
                      <span className="text-muted-foreground mt-0.5 block truncate text-xs">
                        {item.agent.description}
                      </span>
                    )}
                  </span>
                </button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type="button"
                      className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-6 w-6 items-center justify-center opacity-0 transition-opacity group-focus-within/agent:opacity-100 group-hover/agent:opacity-100 data-[state=open]:opacity-100"
                      aria-label={`${item.agent.name} 액션`}
                    >
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-36">
                    <DropdownMenuItem onClick={() => openEditDraft(item.id)}>
                      <Pencil className="size-4" />
                      <span>편집</span>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive"
                      onClick={() => removeAgentPanelFromSession(sessionId, item.id)}
                    >
                      <Trash2 className="size-4" />
                      <span>삭제</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))
          )}
        </div>
      </div>
    </WorkspacePageShell>
  )
}

function SubAgentDraftForm({
  initialAgent,
  onCancel,
  onSave,
}: {
  initialAgent?: Agent
  onCancel: () => void
  onSave: (agent: Agent) => void
}) {
  const [nameDraft, setNameDraft] = useState(initialAgent?.name ?? '')
  const [descriptionDraft, setDescriptionDraft] = useState(initialAgent?.description ?? '')
  const [skillSearch, setSkillSearch] = useState('')
  const [selectedSkillIds, setSelectedSkillIds] = useState<SubAgentSkillId[]>(
    normalizeSkillIds(initialAgent?.skills ?? ['notion']),
  )
  const availableSkills = SUB_AGENT_SKILLS.filter(
    (skill) =>
      !selectedSkillIds.includes(skill.id) &&
      skill.label.toLowerCase().includes(skillSearch.trim().toLowerCase()),
  )
  const selectedSkills = selectedSkillIds
    .map((skillId) => SUB_AGENT_SKILLS.find((skill) => skill.id === skillId))
    .filter((skill): skill is (typeof SUB_AGENT_SKILLS)[number] => skill !== undefined)

  const adoptSkill = (skillId: SubAgentSkillId) => {
    setSelectedSkillIds((current) => (current.includes(skillId) ? current : [...current, skillId]))
  }

  const removeSkill = (skillId: SubAgentSkillId) => {
    setSelectedSkillIds((current) => current.filter((id) => id !== skillId))
  }

  const handleSave = () => {
    const name = nameDraft.trim()
    if (name === '') return
    onSave({
      name,
      description: descriptionDraft.trim(),
      icon: initialAgent?.icon ?? Bot,
      accent: initialAgent?.accent ?? '#111827',
      skills: selectedSkillIds,
    })
  }

  return (
    <div className="border-border border">
      <label className="border-border hover:bg-accent/50 flex items-start gap-3 border-b px-4 py-2 text-sm transition-colors">
        <span className="text-muted-foreground w-28 shrink-0 pt-1 text-xs">이름</span>
        <input
          autoFocus
          value={nameDraft}
          onChange={(event) => setNameDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') handleSave()
            if (event.key === 'Escape') onCancel()
          }}
          className="placeholder:text-muted-foreground/45 focus:bg-accent/20 h-7 min-w-0 flex-1 bg-transparent outline-none"
          placeholder="예: 시장 리서치 담당, QA 검토자, 일정 정리 담당"
        />
      </label>
      <label className="border-border hover:bg-accent/50 flex items-start gap-3 border-b px-4 py-2 text-sm transition-colors">
        <span className="text-muted-foreground w-28 shrink-0 pt-1 text-xs">설명</span>
        <textarea
          value={descriptionDraft}
          onChange={(event) => setDescriptionDraft(event.target.value)}
          rows={2}
          className="placeholder:text-muted-foreground/45 focus:bg-accent/20 min-h-12 min-w-0 flex-1 resize-none bg-transparent leading-6 outline-none"
          placeholder="예: 관련 자료를 찾아 핵심 근거와 출처를 정리합니다."
        />
      </label>
      <div className="flex items-center gap-2 px-4 py-2">
        <button
          type="button"
          onClick={handleSave}
          className="border-border hover:bg-accent/50 border px-2.5 py-1.5 text-xs font-medium transition-colors"
        >
          저장
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-muted-foreground hover:bg-accent/50 hover:text-foreground px-2.5 py-1.5 text-xs font-medium transition-colors"
        >
          취소
        </button>
      </div>
      <div className="border-border border-t px-4 py-3">
        <div className="mb-3 flex items-center justify-between gap-3">
          <span className="text-muted-foreground text-xs">스킬</span>
          <div className="border-border flex h-7 min-w-0 items-center gap-2 border px-2">
            <Search className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
            <input
              value={skillSearch}
              onChange={(event) => setSkillSearch(event.target.value)}
              placeholder="검색"
              className="placeholder:text-muted-foreground/45 h-full w-32 bg-transparent text-xs outline-none"
            />
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground flex h-5 w-5 items-center justify-center"
              aria-label="스킬 추가"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <SkillColumn
            title="채택된 스킬"
            empty="드래그하거나 클릭해서 스킬을 채택하세요."
            onDropSkill={adoptSkill}
          >
            {selectedSkills.map((skill) => (
              <SkillRow key={skill.id} skill={skill} onClick={() => removeSkill(skill.id)} />
            ))}
          </SkillColumn>
          <SkillColumn title="사용 가능한 스킬" empty="검색 결과가 없습니다.">
            {availableSkills.map((skill) => (
              <SkillRow key={skill.id} skill={skill} onClick={() => adoptSkill(skill.id)} />
            ))}
          </SkillColumn>
        </div>
      </div>
    </div>
  )
}

function SkillColumn({
  title,
  empty,
  children,
  onDropSkill,
}: {
  title: string
  empty: string
  children: ReactNode
  onDropSkill?: (skillId: SubAgentSkillId) => void
}) {
  return (
    <div
      className="border-border min-h-36 border"
      onDragOver={(event) => {
        if (onDropSkill !== undefined) {
          event.preventDefault()
        }
      }}
      onDrop={(event) => {
        if (onDropSkill === undefined) return
        const skillId = event.dataTransfer.getData('text/plain') as SubAgentSkillId
        if (SUB_AGENT_SKILLS.some((skill) => skill.id === skillId)) {
          onDropSkill(skillId)
        }
      }}
    >
      <div className="border-border text-muted-foreground border-b px-3 py-2 text-xs">{title}</div>
      <div>
        {children}
        {Array.isArray(children) && children.length === 0 && (
          <p className="text-muted-foreground px-3 py-2 text-xs">{empty}</p>
        )}
      </div>
    </div>
  )
}

function SkillRow({
  skill,
  onClick,
}: {
  skill: (typeof SUB_AGENT_SKILLS)[number]
  onClick: () => void
}) {
  const Icon = skill.icon
  return (
    <button
      type="button"
      draggable
      onDragStart={(event) => {
        event.dataTransfer.setData('text/plain', skill.id)
      }}
      onClick={onClick}
      className="border-border hover:bg-accent/50 flex w-full items-center gap-3 border-b px-3 py-2 text-left text-sm transition-colors last:border-b-0"
    >
      <Icon className="text-muted-foreground h-4 w-4 shrink-0" />
      <span className="min-w-0 flex-1">
        <span className="block truncate">{skill.label}</span>
        <span className="text-muted-foreground mt-0.5 block truncate text-xs">
          {skill.description}
        </span>
      </span>
    </button>
  )
}

function normalizeSkillIds(values: string[]): SubAgentSkillId[] {
  return values.filter((value): value is SubAgentSkillId =>
    SUB_AGENT_SKILLS.some((skill) => skill.id === value),
  )
}

function PromptEntityRow({
  identifier,
  title,
  value,
  multiline = false,
  rows = 3,
  placeholder,
  onChange,
  onDirty,
}: {
  identifier?: string
  title: string
  value: string
  multiline?: boolean
  rows?: number
  placeholder: string
  onChange: (value: string) => void
  onDirty: () => void
}) {
  return (
    <label className="border-border hover:bg-accent/50 flex items-start gap-3 border-b px-4 py-2 text-sm transition-colors last:border-b-0">
      {identifier ? (
        <span className="text-muted-foreground w-20 shrink-0 pt-1 font-mono text-xs">
          {identifier}
        </span>
      ) : null}
      <span className="w-28 shrink-0 truncate pt-1">{title}</span>
      {multiline ? (
        <textarea
          value={value}
          onChange={(event) => {
            onChange(event.target.value)
            onDirty()
          }}
          rows={rows}
          placeholder={placeholder}
          className="placeholder:text-muted-foreground/45 text-muted-foreground focus:bg-accent/20 min-h-16 min-w-0 flex-1 resize-none bg-transparent leading-6 outline-none"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(event) => {
            onChange(event.target.value)
            onDirty()
          }}
          placeholder={placeholder}
          className="placeholder:text-muted-foreground/45 text-muted-foreground focus:bg-accent/20 h-6 min-w-0 flex-1 bg-transparent outline-none"
        />
      )}
    </label>
  )
}

function WorkspacePageShell({
  eyebrow,
  title,
  action,
  children,
}: {
  eyebrow: string
  title: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <main className="bg-background min-w-0 flex-1 overflow-auto p-4 outline-none md:p-6">
      <div className="w-full space-y-6">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs uppercase">{eyebrow}</span>
            <div className="ml-auto">{action}</div>
          </div>
          <h2 className="text-xl font-bold">{title}</h2>
        </div>
        {children}
      </div>
    </main>
  )
}

function formatServerError(message: string) {
  return message.replaceAll('AI WebSocket', '서버').replaceAll('AI 웹소켓', '서버')
}
