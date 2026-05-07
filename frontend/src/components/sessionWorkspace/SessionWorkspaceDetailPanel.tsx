import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileText,
  Loader2,
  MoreHorizontal,
  Play,
  RotateCcw,
} from 'lucide-react'
import { PageTabBar } from '@/components/PageTabBar'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tabs } from '@/components/ui/tabs'
import { SubAgentsPanel } from '@/components/sessionWorkspace/subAgents'
import { AgentStatusPage } from '@/pages/AgentStatusPage'
import { useChatStore } from '@/store/useChatStore'
import type { JsonObject } from '@/realtime/aiRealtimeTypes'
import type { AiModelOption, AiSessionSettingsPatch, RawAiSession } from '@/types/aiChat'
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
    return <SubAgentsPanel sessionId={sessionId} />
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
  const [searchParams, setSearchParams] = useSearchParams()

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
  const currentToolsets = normalizeToolsets(settings.toolsets)
  const currentDelegationPolicy = toJsonObject(settings.delegationPolicy)
  const currentCanDelegate = currentDelegationPolicy.canDelegate === true
  const currentMaxWorkerDepth =
    typeof currentDelegationPolicy.maxWorkerDepth === 'number'
      ? Math.min(1, Math.max(0, Math.floor(currentDelegationPolicy.maxWorkerDepth)))
      : 0
  const currentProfileImage = normalizeAgentProfileImage(
    getString(uiMetadata, 'agentProfileImage') ?? undefined,
  )
  const [purpose, setPurpose] = useState(currentPurpose)
  const [agentName, setAgentName] = useState(currentAgentName)
  const [callName, setCallName] = useState(currentCallName)
  const [persona, setPersona] = useState(currentPersona)
  const [successCriteria, setSuccessCriteria] = useState(currentSuccessCriteria)
  const [constraints, setConstraints] = useState(currentConstraints)
  const [selectedModel, setSelectedModel] = useState(currentModel)
  const [selectedToolsets, setSelectedToolsets] = useState<string[]>(currentToolsets)
  const [canDelegate, setCanDelegate] = useState(currentCanDelegate)
  const [maxWorkerDepth, setMaxWorkerDepth] = useState(currentMaxWorkerDepth)
  const [profileImage, setProfileImage] = useState(currentProfileImage)
  const [modelOptionsLoading, setModelOptionsLoading] = useState(true)
  const [modelOptionsError, setModelOptionsError] = useState<string | null>(null)
  const [modelOptions, setModelOptions] = useState(getModelOptions(undefined))
  const [selectedFamily, setSelectedFamily] = useState<ModelFamily>(inferModelFamily(currentModel))
  const [modelBaseline, setModelBaseline] = useState(currentModel)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [configRevisionsOpen, setConfigRevisionsOpen] = useState(false)

  const modelGroups = useMemo(() => groupModels(modelOptions), [modelOptions])
  const modelFamilies = useMemo(() => getModelFamilies(modelGroups), [modelGroups])
  const effectiveSelectedFamily = modelFamilies.some((family) => family.id === selectedFamily)
    ? selectedFamily
    : (modelFamilies[0]?.id ?? 'gpt')
  const visibleModels = modelGroups[effectiveSelectedFamily]
  const selectedImageIndex = Math.max(
    0,
    CEO_IMAGE_OPTIONS.findIndex((option) => option.src === profileImage),
  )
  const displayName = agentName.trim() || '메인 에이전트'
  const displayRole = callName.trim() || 'CEO'
  const activeTab = getMainAgentTab(searchParams.get('agentTab'))
  const isDirty =
    purpose.trim() !== currentPurpose ||
    agentName.trim() !== currentAgentName ||
    callName.trim() !== currentCallName ||
    persona.trim() !== currentPersona ||
    successCriteria.trim() !== currentSuccessCriteria ||
    constraints.trim() !== currentConstraints ||
    selectedModel !== modelBaseline ||
    profileImage !== currentProfileImage ||
    !stringArraysEqual(selectedToolsets, currentToolsets) ||
    canDelegate !== currentCanDelegate ||
    maxWorkerDepth !== currentMaxWorkerDepth
  const showConfigActionBar =
    (activeTab === 'configuration' || activeTab === 'instructions') && (isDirty || saving)

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
          setModelBaseline(options.model)
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

  useEffect(() => {
    if (!isDirty) return

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isDirty])

  const markDirty = () => {
    setSaved(false)
    setSaveError(null)
  }

  const selectTab = (tab: MainAgentTab) => {
    const nextParams = new URLSearchParams(searchParams)
    if (tab === 'dashboard') {
      nextParams.delete('agentTab')
    } else {
      nextParams.set('agentTab', tab)
    }
    setSearchParams(nextParams)
  }

  const resetDraft = () => {
    setPurpose(currentPurpose)
    setAgentName(currentAgentName)
    setCallName(currentCallName)
    setPersona(currentPersona)
    setSuccessCriteria(currentSuccessCriteria)
    setConstraints(currentConstraints)
    setSelectedModel(modelBaseline)
    setSelectedFamily(inferModelFamily(modelBaseline))
    setSelectedToolsets(currentToolsets)
    setCanDelegate(currentCanDelegate)
    setMaxWorkerDepth(currentMaxWorkerDepth)
    setProfileImage(currentProfileImage)
    setSaveError(null)
    setSaved(false)
  }

  const copyAgentId = async () => {
    try {
      await navigator.clipboard.writeText(sessionId)
      setSaved(true)
      window.setTimeout(() => setSaved(false), 1200)
    } catch {
      setSaveError('에이전트 ID 복사에 실패했습니다.')
    }
  }

  const resetSessionDraft = () => {
    resetDraft()
    setConfigRevisionsOpen(false)
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
    if (selectedModel !== '' && selectedModel !== modelBaseline) {
      settingsPatch.model = selectedModel
    }
    if (!stringArraysEqual(selectedToolsets, currentToolsets)) {
      settingsPatch.toolsets = selectedToolsets
    }
    if (canDelegate !== currentCanDelegate || maxWorkerDepth !== currentMaxWorkerDepth) {
      settingsPatch.delegationPolicy = { canDelegate, maxWorkerDepth }
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
      if (settingsPatch.model !== undefined) {
        setModelBaseline(selectedModel)
      }
      setPurpose(purpose.trim())
      setAgentName(agentName.trim())
      setCallName(callName.trim())
      setPersona(nextPersona)
      setSuccessCriteria(successCriteria.trim())
      setConstraints(constraints.trim())
      setSaved(true)
      window.setTimeout(() => setSaved(false), 1400)
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : '목표 저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <WorkspacePageShell title="메인 에이전트" eyebrow="CEO" hideHeader>
      <div className={`space-y-6 ${showConfigActionBar ? 'pb-24 sm:pb-0' : ''}`}>
        <MainAgentHeader
          callName={displayRole}
          onConfigure={() => selectTab('configuration')}
          onCopyAgentId={copyAgentId}
          onInstructions={() => selectTab('instructions')}
          onReset={resetSessionDraft}
          onRuns={() => selectTab('runs')}
          model={selectedModel}
          name={displayName}
          profileImage={profileImage}
          saved={saved}
          saving={saving}
        />

        <Tabs value={activeTab} onValueChange={(value) => selectTab(value as MainAgentTab)}>
          <PageTabBar
            align="start"
            items={MAIN_AGENT_TABS}
            value={activeTab}
            onValueChange={(value) => selectTab(value as MainAgentTab)}
          />
        </Tabs>

        {activeTab === 'dashboard' && (
          <div className="space-y-4 pt-2">
            <SectionCard title="Profile">
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <SummaryItem label="이름" value={displayName} />
                <SummaryItem label="호칭" value={displayRole} />
                <SummaryItem label="모델" value={selectedModel || '기본 모델'} />
                <SummaryItem label="도구" value={selectedToolsets.join(', ') || '없음'} />
              </div>
            </SectionCard>
            <SectionCard title="Session Goal">
              <div className="space-y-3 text-sm">
                <SummaryItem label="대화 목표" value={purpose || '지정되지 않음'} />
                <SummaryItem label="성공 기준" value={successCriteria || '지정되지 않음'} />
              </div>
            </SectionCard>
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="space-y-4 pt-2">
            <SectionCard title="Skills">
              <div className="grid gap-2 sm:grid-cols-2">
                {PUBLIC_TOOLSET_OPTIONS.map((toolset) => (
                  <ToggleRow
                    key={toolset.id}
                    checked={selectedToolsets.includes(toolset.id)}
                    description={toolset.description}
                    label={toolset.label}
                    onChange={(checked) => {
                      setSelectedToolsets((current) =>
                        checked
                          ? [...current, toolset.id]
                          : current.filter((item) => item !== toolset.id),
                      )
                      markDirty()
                    }}
                  />
                ))}
              </div>
            </SectionCard>
          </div>
        )}

        {activeTab === 'instructions' && (
          <div className="space-y-4 pt-2">
            <SectionCard title="Session Goal">
              <Field label="대화 목표">
                <DraftTextarea
                  minRows={2}
                  onChange={(value) => {
                    setPurpose(value)
                    markDirty()
                  }}
                  placeholder="예: 이번 대화에서는 3분 발표용 서비스 소개안을 완성한다."
                  value={purpose}
                />
              </Field>
              <Field label="성공 기준">
                <DraftTextarea
                  minRows={3}
                  onChange={(value) => {
                    setSuccessCriteria(value)
                    markDirty()
                  }}
                  placeholder="예: 최종 답변에 문제 정의, 해결안, 다음 액션 3개가 포함되어야 합니다."
                  value={successCriteria}
                />
              </Field>
            </SectionCard>
            <SectionCard title="Instructions">
              <Field label="응답 역할">
                <DraftTextarea
                  minRows={4}
                  onChange={(value) => {
                    setPersona(value)
                    markDirty()
                  }}
                  placeholder="예: PM처럼 질문하고, 근거가 부족하면 먼저 확인하며, 답변은 실행 항목 중심으로 정리한다."
                  value={persona}
                />
              </Field>
              <Field label="제약">
                <DraftTextarea
                  minRows={3}
                  onChange={(value) => {
                    setConstraints(value)
                    markDirty()
                  }}
                  placeholder="예: 추측하지 말고 모르는 내용은 확인 질문으로 남겨주세요."
                  value={constraints}
                />
              </Field>
            </SectionCard>
          </div>
        )}

        {activeTab === 'configuration' && (
          <div className="max-w-5xl space-y-4 pt-2">
            <SectionCard title="Identity">
              <div className="grid gap-4 sm:grid-cols-[10rem_minmax(0,1fr)]">
                <Field label="프로필 이미지">
                  <AgentImageStepper
                    profileImage={profileImage}
                    selectedImageIndex={selectedImageIndex}
                    onProfileImageChange={(image) => {
                      setProfileImage(image)
                      markDirty()
                    }}
                  />
                </Field>
                <div className="space-y-3">
                  <Field label="이름">
                    <DraftInput
                      onChange={(value) => {
                        setAgentName(value)
                        markDirty()
                      }}
                      placeholder="예: 기획 도우미"
                      value={agentName}
                    />
                  </Field>
                  <Field label="호칭">
                    <DraftInput
                      onChange={(value) => {
                        setCallName(value)
                        markDirty()
                      }}
                      placeholder="예: 팀장님, 사용자님"
                      value={callName}
                    />
                  </Field>
                </div>
              </div>
            </SectionCard>
            <SectionCard title="Execution">
              <Field label="Default environment">
                <select className={`${inputClass} cursor-not-allowed opacity-70`} value="" disabled>
                  <option value="">Company default (Local)</option>
                </select>
              </Field>
            </SectionCard>
            <SectionCard title="Adapter">
              <ModelSelector
                effectiveSelectedFamily={effectiveSelectedFamily}
                modelFamilies={modelFamilies}
                modelOptionsError={modelOptionsError}
                modelOptionsLoading={modelOptionsLoading}
                onModelSelect={(modelId) => {
                  setSelectedModel(modelId)
                  markDirty()
                }}
                onFamilySelect={setSelectedFamily}
                selectedModel={selectedModel}
                visibleModels={visibleModels}
              />
            </SectionCard>
            <SectionCard title="Permissions & Configuration">
              <div className="grid gap-2 sm:grid-cols-2">
                {PUBLIC_TOOLSET_OPTIONS.map((toolset) => (
                  <ToggleRow
                    key={toolset.id}
                    checked={selectedToolsets.includes(toolset.id)}
                    description={toolset.description}
                    label={toolset.label}
                    onChange={(checked) => {
                      setSelectedToolsets((current) =>
                        checked
                          ? [...current, toolset.id]
                          : current.filter((item) => item !== toolset.id),
                      )
                      markDirty()
                    }}
                  />
                ))}
              </div>
            </SectionCard>
            <SectionCard title="Run Policy">
              <ToggleRow
                checked={canDelegate}
                description="승인된 범위 안에서 서브 작업을 맡길 수 있게 합니다."
                label="Wake on demand"
                onChange={(checked) => {
                  setCanDelegate(checked)
                  if (!checked) setMaxWorkerDepth(0)
                  markDirty()
                }}
              />
              {canDelegate && (
                <Field label="Max concurrent runs">
                  <select
                    className={inputClass}
                    value={maxWorkerDepth}
                    onChange={(event) => {
                      setMaxWorkerDepth(Number(event.target.value))
                      markDirty()
                    }}
                  >
                    <option value={0}>0</option>
                    <option value={1}>1</option>
                  </select>
                </Field>
              )}
            </SectionCard>
            <div className="space-y-3">
              <h3 className="text-sm font-medium">API Keys</h3>
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
                onClick={() => setConfigRevisionsOpen((open) => !open)}
              >
                {configRevisionsOpen ? (
                  <ChevronLeft className="text-muted-foreground h-3.5 w-3.5 -rotate-90" />
                ) : (
                  <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
                )}
                Configuration Revisions
                <span className="text-muted-foreground text-xs font-normal">0</span>
              </button>
              {configRevisionsOpen && (
                <p className="text-muted-foreground mt-3 text-sm">
                  No configuration revisions yet.
                </p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="max-w-5xl space-y-4 pt-2">
            <SectionCard title="Runs">
              <div className="space-y-3 text-sm">
                <SummaryItem label="최근 메시지" value={session.last_message || '없음'} />
                <SummaryItem label="최근 메시지 시각" value={session.last_message_at || '없음'} />
                <SummaryItem
                  label="최근 실행 상태"
                  value={session.last_task_run_status || '없음'}
                />
              </div>
            </SectionCard>
          </div>
        )}

        {activeTab === 'budget' && (
          <div className="space-y-4 pt-2">
            <div className="max-w-3xl">
              <SectionCard title="Budget">
                <div className="grid gap-3 text-sm sm:grid-cols-3">
                  <SummaryItem label="Monthly limit" value="정책 없음" />
                  <SummaryItem label="Current spend" value="사용량 데이터 없음" />
                  <SummaryItem label="Run budget" value="연동 전" />
                </div>
              </SectionCard>
            </div>
          </div>
        )}

        {saveError && (
          <p className="text-destructive text-sm" aria-live="polite">
            {saveError}
          </p>
        )}
        {(isDirty || saving) && (
          <div className="border-border bg-background/95 fixed inset-x-0 bottom-0 z-30 border-t backdrop-blur-sm sm:hidden">
            <div className="flex items-center justify-end gap-2 px-3 py-2 pb-[max(env(safe-area-inset-bottom),0.5rem)]">
              <Button variant="ghost" size="sm" onClick={resetDraft} disabled={saving}>
                취소
              </Button>
              <Button size="sm" onClick={() => void handleSave()} disabled={saving || !isDirty}>
                {saving ? '저장 중' : '저장'}
              </Button>
            </div>
          </div>
        )}
        {(isDirty || saving) && (
          <div className="fixed right-6 bottom-6 z-30 hidden sm:block">
            <div className="bg-background/90 border-border flex items-center gap-2 rounded-lg border px-3 py-1.5 shadow-lg backdrop-blur-sm">
              <Button variant="ghost" size="sm" onClick={resetDraft} disabled={saving}>
                취소
              </Button>
              <Button size="sm" onClick={() => void handleSave()} disabled={saving || !isDirty}>
                {saving ? '저장 중' : '저장'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </WorkspacePageShell>
  )
}

type MainAgentTab = 'dashboard' | 'instructions' | 'skills' | 'configuration' | 'runs' | 'budget'

const MAIN_AGENT_TABS: Array<{ value: MainAgentTab; label: string }> = [
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'instructions', label: 'Instructions' },
  { value: 'skills', label: 'Skills' },
  { value: 'configuration', label: 'Configuration' },
  { value: 'runs', label: 'Runs' },
  { value: 'budget', label: 'Budget' },
]

const inputClass =
  'border-border placeholder:text-muted-foreground/40 focus-visible:ring-ring w-full rounded-md border bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2'

const CEO_IMAGE_OPTIONS = [
  { id: 'desk', label: '책상', src: '/assets/agents/ceo/ceo_desk.png' },
  { id: 'explain', label: '설명', src: '/assets/agents/ceo/ceo_explain.png' },
  { id: 'profile', label: '프로필', src: '/assets/agents/ceo/ceo_profile.png' },
] as const

const PUBLIC_TOOLSET_OPTIONS = [
  { id: 'session', label: 'Session', description: '세션 기록과 맥락을 사용합니다.' },
  { id: 'planning', label: 'Planning', description: '계획/진행 상태 도구를 사용합니다.' },
  { id: 'web', label: 'Web', description: '웹 검색/조회 도구를 사용합니다.' },
  { id: 'skills', label: 'Skills', description: '등록된 스킬 도구를 사용합니다.' },
  { id: 'safe', label: 'Safe', description: '안전한 기본 도구만 허용합니다.' },
] as const

function MainAgentHeader({
  callName,
  model,
  name,
  onConfigure,
  onCopyAgentId,
  onInstructions,
  onReset,
  onRuns,
  profileImage,
  saved,
  saving,
}: {
  callName: string
  model: string
  name: string
  onConfigure: () => void
  onCopyAgentId: () => void
  onInstructions: () => void
  onReset: () => void
  onRuns: () => void
  profileImage: string
  saved: boolean
  saving: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onConfigure}
          className="bg-accent hover:bg-accent/80 flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
          aria-label="메인 에이전트 프로필 설정 열기"
        >
          <img src={profileImage} alt="" className="h-10 w-10 object-contain" draggable={false} />
        </button>
        <div className="min-w-0">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="truncate text-2xl font-bold">{name}</h2>
            {saved && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                <Check className="h-3.5 w-3.5" />
                저장됨
              </span>
            )}
            {saving && (
              <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                저장 중
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1 truncate text-sm">
            {callName} · {model || '기본 모델'}
          </p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-2">
        <Button variant="outline" size="sm" onClick={onInstructions}>
          <FileText className="h-3.5 w-3.5 sm:mr-1" />
          <span className="hidden sm:inline">Instructions</span>
        </Button>
        <Button variant="outline" size="sm" onClick={onRuns}>
          <Play className="h-3.5 w-3.5 sm:mr-1" />
          <span className="hidden sm:inline">Runs</span>
        </Button>
        <span className="border-border bg-muted/40 hidden rounded-full border px-2 py-0.5 text-xs sm:inline">
          active
        </span>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon-xs">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-44 p-1" align="end">
            <button
              type="button"
              onClick={onCopyAgentId}
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs"
            >
              <Copy className="size-4" />
              <span>Copy Agent ID</span>
            </button>
            <button
              type="button"
              onClick={onReset}
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs"
            >
              <RotateCcw className="size-4" />
              <span>Reset Draft</span>
            </button>
            <button
              type="button"
              onClick={onRuns}
              className="hover:bg-accent/50 flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs"
            >
              <Play className="size-4" />
              <span>View Runs</span>
            </button>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  )
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium">{title}</h3>
      <div className="border-border bg-background space-y-4 rounded-lg border p-4">{children}</div>
    </section>
  )
}

function SummaryItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className="mt-1 min-w-0 text-sm break-words">{value}</div>
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

function DraftInput({
  onChange,
  placeholder,
  value,
}: {
  onChange: (value: string) => void
  placeholder: string
  value: string
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className={inputClass}
    />
  )
}

function DraftTextarea({
  minRows,
  onChange,
  placeholder,
  value,
}: {
  minRows: number
  onChange: (value: string) => void
  placeholder: string
  value: string
}) {
  return (
    <textarea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      rows={minRows}
      className={`${inputClass} resize-y leading-6`}
    />
  )
}

function ToggleRow({
  checked,
  description,
  label,
  onChange,
}: {
  checked: boolean
  description: string
  label: string
  onChange: (checked: boolean) => void
}) {
  return (
    <label className="border-border hover:bg-accent/40 flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="border-border mt-0.5 h-4 w-4 rounded"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium">{label}</span>
        <span className="text-muted-foreground mt-0.5 block text-xs leading-5">{description}</span>
      </span>
    </label>
  )
}

function normalizeAgentProfileImage(value: string | undefined) {
  if (value !== undefined && CEO_IMAGE_OPTIONS.some((option) => option.src === value)) {
    return value
  }
  return CEO_IMAGE_OPTIONS[0].src
}

function normalizeToolsets(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return Array.from(
    new Set(value.filter((item): item is string => typeof item === 'string' && item.trim() !== '')),
  )
}

function stringArraysEqual(left: string[], right: string[]) {
  if (left.length !== right.length) return false
  const leftSet = new Set(left)
  return right.every((item) => leftSet.has(item))
}

function getMainAgentTab(value: string | null): MainAgentTab {
  if (value === 'overview') return 'dashboard'
  if (value === 'activity') return 'runs'
  return MAIN_AGENT_TABS.some((tab) => tab.value === value) ? (value as MainAgentTab) : 'dashboard'
}

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
            className={`border-b px-5 py-2 text-sm font-medium transition-colors ${
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

      <div className="border-border max-h-80 overflow-y-auto rounded-lg border">
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

function AgentImageStepper({
  onProfileImageChange,
  profileImage,
  selectedImageIndex,
}: {
  onProfileImageChange: (image: string) => void
  profileImage: string
  selectedImageIndex: number
}) {
  const selectedImage = CEO_IMAGE_OPTIONS[selectedImageIndex]

  return (
    <div className="flex w-full min-w-0 items-center gap-2" aria-label="에이전트 이미지">
      <button
        type="button"
        onClick={() => {
          const nextIndex =
            (selectedImageIndex - 1 + CEO_IMAGE_OPTIONS.length) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="이전 에이전트 이미지"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="bg-accent hover:bg-accent/80 flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
        aria-label={`${selectedImage?.label ?? '메인 에이전트'} 이미지 변경`}
      >
        <img src={profileImage} alt="" className="h-10 w-10 object-contain" draggable={false} />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="다음 에이전트 이미지"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
      <span className="text-muted-foreground min-w-0 truncate text-xs">
        {selectedImage?.label ?? '메인 에이전트'}
      </span>
    </div>
  )
}

function WorkspacePageShell({
  eyebrow,
  title,
  action,
  children,
  hideHeader = false,
}: {
  eyebrow: string
  title: string
  action?: ReactNode
  children: ReactNode
  hideHeader?: boolean
}) {
  return (
    <main className="bg-background min-w-0 flex-1 overflow-auto p-4 outline-none md:p-6">
      <div className="w-full space-y-6">
        {!hideHeader && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-xs uppercase">{eyebrow}</span>
              <div className="ml-auto">{action}</div>
            </div>
            <h2 className="text-xl font-bold">{title}</h2>
          </div>
        )}
        {children}
      </div>
    </main>
  )
}

function formatServerError(message: string) {
  return message.replaceAll('AI WebSocket', '서버').replaceAll('AI 웹소켓', '서버')
}
