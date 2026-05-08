import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import {
  Activity,
  BarChart3,
  Check,
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  Play,
} from 'lucide-react'
import { PageTabBar } from '@/components/PageTabBar'
import { Button } from '@/components/ui/button'
import { Tabs } from '@/components/ui/tabs'
import {
  AgentDetailHeader,
  type AgentRunItemData,
  AgentBudgetPanel,
  AgentConfigurationPanel,
  AgentDashboardPanel,
  AgentInstructionsBundlePanel,
  AgentInstructionsPanel,
  AgentAdapterTypeDropdown,
  AgentModelDropdown,
  AgentRunsPanel,
  AgentSectionCard,
  AgentSkillsLibraryPanel,
  AgentSkillsPanel,
} from '@/components/sessionWorkspace/AgentDetailPanels'
import { IssueBoardPanel } from '@/components/sessionWorkspace/issueBoard'
import { SubAgentsPanel } from '@/components/sessionWorkspace/subAgents'
import { getTime } from '@/components/taskRuns/stepRunActivityPanel/activityPanelText'
import { AgentStatusPage } from '@/pages/AgentStatusPage'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useChatStore } from '@/store/useChatStore'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import { useUIStore } from '@/store/useUIStore'
import type { JsonObject, RawTaskEventPayload } from '@/realtime/aiRealtimeTypes'
import type { AiSessionSettingsPatch, ChatMessageView, RawAiSession } from '@/types/aiChat'
import type { RawTaskRun } from '@/types/taskRuns'
import { isInternalStepAnchorEvent, toTaskRunSummaryView } from '@/utils/taskRunStatusView'
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

const EMPTY_MESSAGES: never[] = []

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

  if (activePanel === 'issueBoard') {
    return <IssueBoardPanel sessionId={sessionId} />
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
  const authenticatedReady = useAiRealtimeStore((state) => state.authenticatedReady)
  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const messages = useChatStore(
    (state) => state.messagesBySessionId[session.session_id] ?? EMPTY_MESSAGES,
  )
  const fetchMessages = useChatStore((state) => state.fetchMessages)
  const updateSession = useChatStore((state) => state.updateSession)
  const updateSessionSettings = useChatStore((state) => state.updateSessionSettings)
  const fetchModelOptions = useChatStore((state) => state.fetchModelOptions)
  const taskRunsById = useTaskRunStore((state) => state.taskRunsById)
  const eventsByTaskRunId = useTaskRunStore((state) => state.eventsByTaskRunId)
  const fetchActiveTaskRuns = useTaskRunStore((state) => state.fetchActiveTaskRuns)
  const [searchParams, setSearchParams] = useSearchParams()

  const metadata = useMemo(() => toJsonObject(session.metadata), [session.metadata])
  const uiMetadata = useMemo(() => toJsonObject(metadata.ui), [metadata])
  const settings = useMemo(() => toJsonObject(session.settings), [session.settings])
  const sessionId = session.session_id
  const currentAgentName = getString(uiMetadata, 'agentName') ?? ''
  const currentCallName = getString(uiMetadata, 'callName') ?? ''
  const currentCapabilities = getString(uiMetadata, 'agentCapabilities') ?? ''
  const currentSkillIds = normalizeMainAgentSkillIds(uiMetadata.agentSkills)
  const currentPersona =
    getString(settings, 'systemPrompt') ?? getString(settings, 'system_prompt') ?? ''
  const currentInstructionsEntryFile = getString(uiMetadata, 'instructionsEntryFile') ?? 'AGENTS.md'
  const currentInstructionsFiles = getInstructionsFiles(uiMetadata.instructionsFiles)
  const currentInstructionsMode =
    getString(uiMetadata, 'instructionsMode') === 'external' ? 'external' : 'managed'
  const currentInstructionsRootPath = getString(uiMetadata, 'instructionsRootPath') ?? ''
  const currentModel = getString(settings, 'model') ?? ''
  const currentDelegationPolicy = toJsonObject(settings.delegationPolicy)
  const currentCanDelegate = currentDelegationPolicy.canDelegate === true
  const currentProfileImage = normalizeAgentProfileImage(
    getString(uiMetadata, 'agentProfileImage') ?? undefined,
  )
  const [agentName, setAgentName] = useState(currentAgentName)
  const [callName, setCallName] = useState(currentCallName)
  const [capabilities, setCapabilities] = useState(currentCapabilities)
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>(currentSkillIds)
  const [persona, setPersona] = useState(currentPersona)
  const [instructionsEntryFile, setInstructionsEntryFile] = useState(currentInstructionsEntryFile)
  const [instructionsFiles, setInstructionsFiles] = useState(currentInstructionsFiles)
  const [instructionsMode, setInstructionsMode] = useState<'managed' | 'external'>(
    currentInstructionsMode,
  )
  const [instructionsRootPath, setInstructionsRootPath] = useState(currentInstructionsRootPath)
  const [selectedModel, setSelectedModel] = useState(currentModel)
  const [canDelegate, setCanDelegate] = useState(currentCanDelegate)
  const [profileImage, setProfileImage] = useState(currentProfileImage)
  const [modelOptionsLoading, setModelOptionsLoading] = useState(authenticatedReady)
  const [modelOptionsError, setModelOptionsError] = useState<string | null>(null)
  const [modelOptions, setModelOptions] = useState(getModelOptions(undefined))
  const [selectedFamily, setSelectedFamily] = useState<ModelFamily>(inferModelFamily(currentModel))
  const [modelBaseline, setModelBaseline] = useState(currentModel)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const setSettingsOpen = useUIStore((state) => state.setSettingsOpen)

  const modelGroups = useMemo(() => groupModels(modelOptions), [modelOptions])
  const modelFamilies = useMemo(() => getModelFamilies(modelGroups), [modelGroups])
  const effectiveSelectedFamily = modelFamilies.some((family) => family.id === selectedFamily)
    ? selectedFamily
    : (modelFamilies[0]?.id ?? 'gpt')
  const visibleModels = modelGroups[effectiveSelectedFamily]
  const visibleModelOptions = visibleModels.map((model) => ({
    value: model.id,
    label: model.label,
    description: model.provider ?? effectiveSelectedFamily,
  }))
  const selectedImageIndex = Math.max(
    0,
    CEO_IMAGE_OPTIONS.findIndex((option) => option.src === profileImage),
  )
  const displayName = agentName.trim() || '메인 에이전트'
  const displayRole = callName.trim() || 'CEO'
  const activeTab = getMainAgentTab(searchParams.get('agentTab'))
  const isDirty =
    agentName.trim() !== currentAgentName ||
    callName.trim() !== currentCallName ||
    capabilities.trim() !== currentCapabilities ||
    !stringArraysEqual(selectedSkillIds, currentSkillIds) ||
    persona.trim() !== currentPersona ||
    instructionsEntryFile.trim() !== currentInstructionsEntryFile ||
    !shallowStringRecordEqual(instructionsFiles, currentInstructionsFiles) ||
    instructionsMode !== currentInstructionsMode ||
    instructionsRootPath.trim() !== currentInstructionsRootPath ||
    selectedModel !== modelBaseline ||
    profileImage !== currentProfileImage ||
    canDelegate !== currentCanDelegate
  const showConfigActionBar =
    (activeTab === 'configuration' || activeTab === 'instructions') && (isDirty || saving)
  const sessionRuns = useMemo(
    () => buildSessionRunItems(session, messages, taskRunsById, eventsByTaskRunId),
    [eventsByTaskRunId, messages, session, taskRunsById],
  )

  useEffect(() => {
    if (!authenticatedReady || commandClient === null || sessionId.startsWith('pending_session_')) {
      return
    }

    let cancelled = false
    void Promise.all([fetchMessages(sessionId), fetchActiveTaskRuns(sessionId)]).catch((error) => {
      if (cancelled) return
      console.error(error)
    })

    return () => {
      cancelled = true
    }
  }, [authenticatedReady, commandClient, fetchActiveTaskRuns, fetchMessages, sessionId])

  useEffect(() => {
    if (!authenticatedReady || commandClient === null) {
      return
    }

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
  }, [authenticatedReady, commandClient, currentModel, fetchModelOptions, sessionId])

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
    setAgentName(currentAgentName)
    setCallName(currentCallName)
    setCapabilities(currentCapabilities)
    setSelectedSkillIds(currentSkillIds)
    setPersona(currentPersona)
    setInstructionsEntryFile(currentInstructionsEntryFile)
    setInstructionsFiles(currentInstructionsFiles)
    setInstructionsMode(currentInstructionsMode)
    setInstructionsRootPath(currentInstructionsRootPath)
    setSelectedModel(modelBaseline)
    setSelectedFamily(inferModelFamily(modelBaseline))
    setCanDelegate(currentCanDelegate)
    setProfileImage(currentProfileImage)
    setSaveError(null)
    setSaved(false)
  }

  const handleSave = async () => {
    const nextUiMetadata: JsonObject = { ...uiMetadata }
    setOptionalUiString(nextUiMetadata, 'agentName', agentName)
    setOptionalUiString(nextUiMetadata, 'callName', callName)
    setOptionalUiString(nextUiMetadata, 'agentCapabilities', capabilities)
    if (selectedSkillIds.length === 0) {
      delete nextUiMetadata.agentSkills
    } else {
      nextUiMetadata.agentSkills = selectedSkillIds
    }
    setOptionalUiString(nextUiMetadata, 'agentProfileImage', profileImage)
    setOptionalUiString(nextUiMetadata, 'instructionsEntryFile', instructionsEntryFile)
    if (Object.keys(instructionsFiles).length === 0) {
      delete nextUiMetadata.instructionsFiles
    } else {
      nextUiMetadata.instructionsFiles = instructionsFiles
    }
    setOptionalUiString(nextUiMetadata, 'instructionsMode', instructionsMode)
    setOptionalUiString(nextUiMetadata, 'instructionsRootPath', instructionsRootPath)

    const settingsPatch: AiSessionSettingsPatch = {}
    const nextPersona = persona.trim()
    if (nextPersona !== currentPersona) {
      settingsPatch.systemPrompt = nextPersona
    }
    if (selectedModel !== '' && selectedModel !== modelBaseline) {
      settingsPatch.model = selectedModel
    }
    if (canDelegate !== currentCanDelegate) {
      settingsPatch.delegationPolicy = { canDelegate }
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
      setAgentName(agentName.trim())
      setCallName(callName.trim())
      setCapabilities(capabilities.trim())
      setPersona(nextPersona)
      setInstructionsEntryFile(instructionsEntryFile.trim() || 'AGENTS.md')
      setInstructionsRootPath(instructionsRootPath.trim())
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
          <AgentDashboardPanel
            costs={[
              { label: '입력 토큰', value: '0' },
              { label: '출력 토큰', value: '0' },
              { label: '캐시 토큰', value: '0' },
              { label: '총 비용', value: '$0.00' },
            ]}
            latestRun={sessionRuns[0] ?? null}
            metrics={[
              {
                icon: Activity,
                label: '실행 현황',
                value: formatSessionRunStatus(session.last_task_run_status),
                description: '최근 14일',
              },
              {
                icon: FileText,
                label: '담당 작업',
                value: '0',
                description: '최근 14일',
              },
              {
                icon: BarChart3,
                label: '상태별 작업',
                value: '0',
                description: '최근 14일',
              },
              {
                icon: Play,
                label: '완료 횟수',
                value: session.last_message_at ? '1+' : '0',
                description: '최근 14일',
              },
            ]}
            recentTitle="최근 작업"
            recentEmptyText="최근 작업이 없습니다."
            recentItems={[]}
          />
        )}

        {activeTab === 'skills' && (
          <AgentSkillsPanel>
            <AgentSkillsLibraryPanel
              adapterLabel="세션"
              applicationLabel="에이전트 실행 시 적용"
              rows={MAIN_AGENT_SKILL_OPTIONS.map((skill) => ({
                key: skill.id,
                name: skill.label,
                description: skill.description,
                checked: selectedSkillIds.includes(skill.id),
                linkLabel: 'View',
              }))}
              selectedCount={selectedSkillIds.length}
              onSkillToggle={(skillId, checked) => {
                setSelectedSkillIds((current) =>
                  checked ? [...current, skillId] : current.filter((item) => item !== skillId),
                )
                markDirty()
              }}
            />
          </AgentSkillsPanel>
        )}

        {activeTab === 'instructions' && (
          <AgentInstructionsPanel>
            <AgentInstructionsBundlePanel
              content={persona}
              entryFile={instructionsEntryFile}
              files={instructionsFiles}
              mode={instructionsMode}
              rootPath={instructionsRootPath}
              onContentChange={(value) => {
                setPersona(value)
                markDirty()
              }}
              onEntryFileChange={(value) => {
                setInstructionsEntryFile(value)
                markDirty()
              }}
              onFilesChange={(value) => {
                setInstructionsFiles(value)
                markDirty()
              }}
              onModeChange={(value) => {
                setInstructionsMode(value)
                markDirty()
              }}
              onRootPathChange={(value) => {
                setInstructionsRootPath(value)
                markDirty()
              }}
            />
          </AgentInstructionsPanel>
        )}

        {activeTab === 'configuration' && (
          <AgentConfigurationPanel>
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.82fr)]">
              <div className="space-y-4">
                <AgentSectionCard title="프로필">
                  <div className="grid gap-4 sm:grid-cols-[14rem_minmax(0,1fr)]">
                    <div aria-label="프로필 이미지">
                      <AgentImageStepper
                        profileImage={profileImage}
                        selectedImageIndex={selectedImageIndex}
                        onProfileImageChange={(image) => {
                          setProfileImage(image)
                          markDirty()
                        }}
                      />
                    </div>
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
                </AgentSectionCard>
                <AgentSectionCard title="실행 환경">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Field label="기본 환경">
                      <select
                        className={`${inputClass} cursor-not-allowed opacity-70`}
                        value=""
                        disabled
                      >
                        <option value="">회사 기본값 (로컬)</option>
                      </select>
                    </Field>
                    <Field label="역할">
                      <input className={`${inputClass} opacity-70`} value="CEO" disabled readOnly />
                    </Field>
                    <Field label="상위 에이전트">
                      <input
                        className={`${inputClass} opacity-70`}
                        value="Root"
                        disabled
                        readOnly
                      />
                    </Field>
                  </div>
                </AgentSectionCard>
                <AgentSectionCard title="역할과 능력">
                  <Field label="할 수 있는 일">
                    <DraftTextarea
                      minRows={3}
                      onChange={(value) => {
                        setCapabilities(value)
                        markDirty()
                      }}
                      placeholder="이 에이전트가 할 수 있는 일을 적어주세요."
                      value={capabilities}
                    />
                  </Field>
                </AgentSectionCard>
              </div>
              <div className="space-y-4">
                <AgentSectionCard title="연결 방식">
                  <ModelSelector
                    effectiveSelectedFamily={effectiveSelectedFamily}
                    modelFamilies={modelFamilies}
                    onFamilySelect={setSelectedFamily}
                  />
                </AgentSectionCard>
                <AgentSectionCard title="모델">
                  <Field label="모델">
                    {authenticatedReady && modelOptionsLoading && (
                      <span className="text-muted-foreground mb-1 inline-flex items-center gap-1.5 text-xs">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        조회 중
                      </span>
                    )}
                    {authenticatedReady && modelOptionsError ? (
                      <p className="text-destructive text-sm">
                        {formatServerError(modelOptionsError)}
                      </p>
                    ) : (
                      <AgentModelDropdown
                        value={selectedModel}
                        options={visibleModelOptions}
                        onChange={(modelId) => {
                          setSelectedModel(modelId)
                          markDirty()
                        }}
                        allowDefault
                      />
                    )}
                  </Field>
                </AgentSectionCard>
                <AgentSectionCard title="실행 규칙">
                  <ToggleRow
                    checked={canDelegate}
                    description="세션 안에서 필요한 서브에이전트를 호출할 수 있습니다."
                    label="서브에이전트 호출 허용"
                    onChange={(checked) => {
                      setCanDelegate(checked)
                      markDirty()
                    }}
                  />
                </AgentSectionCard>
                <AgentSectionCard title="API 키">
                  <div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSettingsOpen(true, 'apiKeys')}
                    >
                      API 키 설정 열기
                    </Button>
                  </div>
                </AgentSectionCard>
              </div>
            </div>
          </AgentConfigurationPanel>
        )}

        {activeTab === 'runs' && (
          <AgentRunsPanel emptyText="아직 실행 기록이 없습니다." items={sessionRuns} />
        )}

        {activeTab === 'budget' && (
          <AgentBudgetPanel
            summary={{
              amountLabel: '사용 안 함',
              observedLabel: '$0.00',
              remainingLabel: '제한 없음',
              scopeName: displayName,
              scopeType: '에이전트',
              status: 'healthy',
              utilizationPercent: 0,
              warnPercent: 80,
              windowLabel: '월간 예산',
            }}
          />
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

function buildSessionRunItems(
  session: RawAiSession,
  messages: ChatMessageView[],
  taskRunsById: Record<string, RawTaskRun>,
  eventsByTaskRunId: Record<string, RawTaskEventPayload[]>,
): AgentRunItemData[] {
  const ids = new Set<string>()

  messages.forEach((message) => {
    if (message.taskRunId !== undefined) {
      ids.add(message.taskRunId)
    }
  })

  Object.values(taskRunsById).forEach((taskRun) => {
    if (taskRun.session_id === session.session_id) {
      ids.add(taskRun.task_run_id)
    }
  })

  if (typeof session.active_task_run_id === 'string' && session.active_task_run_id.trim()) {
    ids.add(session.active_task_run_id)
  }

  const runItems = [...ids]
    .map((taskRunId) =>
      buildSessionRunItem(taskRunId, session, messages, taskRunsById[taskRunId], eventsByTaskRunId),
    )
    .sort((first, second) => second.sortTime - first.sortTime)
    .map(toAgentRunItem)

  if (runItems.length > 0 || (!session.last_message && !session.last_task_run_status)) {
    return runItems
  }

  return [
    {
      id: session.session_id,
      status: normalizeRunStatus(session.last_task_run_status),
      source: 'chat',
      createdAt: formatRunTimestamp(getTime(session.last_message_at)),
      summary: session.last_message || '아직 요약이 없습니다.',
      tokens: '0 tok',
      cost: '$0.00',
      adapter: 'openai',
    },
  ]
}

function buildSessionRunItem(
  taskRunId: string,
  session: RawAiSession,
  messages: ChatMessageView[],
  taskRun: RawTaskRun | undefined,
  eventsByTaskRunId: Record<string, RawTaskEventPayload[]>,
): AgentRunItemData & { sortTime: number } {
  const events = (eventsByTaskRunId[taskRunId] ?? []).filter(
    (event) => !isInternalStepAnchorEvent(event),
  )
  const summary = toTaskRunSummaryView(taskRun, events)
  const relatedMessages = messages.filter((message) => message.taskRunId === taskRunId)
  const prompt = relatedMessages.find((message) => message.role === 'user')?.content
  const answer = [...relatedMessages]
    .reverse()
    .find((message) => message.role === 'assistant')?.content
  const sortTime = getRunSortTime(taskRun, events, relatedMessages, session)

  return {
    id: taskRunId,
    status: normalizeRunStatus(summary.tone),
    source: 'chat',
    createdAt: formatRunTimestamp(sortTime),
    summary:
      getCompactRunSummary(prompt) ??
      getCompactRunSummary(answer) ??
      getCompactRunSummary(summary.title) ??
      '아직 요약이 없습니다.',
    tokens: '0 tok',
    cost: '$0.00',
    adapter: 'openai',
    model: getString(toJsonObject(session.settings), 'model') ?? undefined,
    sortTime,
  }
}

function toAgentRunItem(item: AgentRunItemData & { sortTime: number }): AgentRunItemData {
  return {
    id: item.id,
    status: item.status,
    source: item.source,
    createdAt: item.createdAt,
    summary: item.summary,
    tokens: item.tokens,
    cost: item.cost,
    adapter: item.adapter,
    model: item.model,
  }
}

function getRunSortTime(
  taskRun: RawTaskRun | undefined,
  events: RawTaskEventPayload[],
  messages: ChatMessageView[],
  session: RawAiSession,
) {
  const eventTimes = events.map((event) => getTime(event.occurred_at))
  const messageTimes = messages.map((message) => getTime(message.createdAt))
  return Math.max(
    getTime(taskRun?.completed_at),
    getTime(taskRun?.updated_at),
    getTime(taskRun?.created_at),
    getTime(session.last_message_at),
    ...eventTimes,
    ...messageTimes,
    0,
  )
}

function getCompactRunSummary(value?: string | null) {
  const text = typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : ''
  if (!text) return undefined
  return text.length > 120 ? `${text.slice(0, 117)}...` : text
}

function formatRunTimestamp(time: number) {
  if (time <= 0) return undefined
  return new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(time))
}

function normalizeRunStatus(status?: string | null) {
  switch (status) {
    case 'completed':
    case 'COMPLETED':
      return 'succeeded'
    case 'failed':
    case 'FAILED':
    case 'CANCELLED':
    case 'CANCELED':
      return 'failed'
    case 'running':
    case 'RUNNING':
      return 'running'
    case 'waiting':
    case 'WAITING':
    case 'PENDING':
      return 'waiting'
    case 'idle':
    case undefined:
    case null:
      return 'pending'
    default:
      return status
  }
}

function formatSessionRunStatus(status?: string | null) {
  switch (normalizeRunStatus(status)) {
    case 'succeeded':
      return '완료'
    case 'running':
      return '실행 중'
    case 'waiting':
      return '대기 중'
    case 'pending':
      return '준비 중'
    case 'failed':
      return '오류'
    default:
      return status || '없음'
  }
}

function getInstructionsFiles(value: unknown): Record<string, string> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return {}
  return Object.fromEntries(
    Object.entries(value).filter(
      (entry): entry is [string, string] =>
        typeof entry[0] === 'string' && typeof entry[1] === 'string',
    ),
  )
}

function shallowStringRecordEqual(left: Record<string, string>, right: Record<string, string>) {
  const leftEntries = Object.entries(left)
  const rightEntries = Object.entries(right)
  if (leftEntries.length !== rightEntries.length) return false
  return leftEntries.every(([key, value]) => right[key] === value)
}

type MainAgentTab = 'dashboard' | 'instructions' | 'skills' | 'configuration' | 'runs' | 'budget'

const MAIN_AGENT_TABS: Array<{ value: MainAgentTab; label: string }> = [
  { value: 'dashboard', label: '대시보드' },
  { value: 'instructions', label: '지침' },
  { value: 'skills', label: '스킬' },
  { value: 'configuration', label: '설정' },
  { value: 'runs', label: '실행 기록' },
  { value: 'budget', label: '예산' },
]

const inputClass =
  'border-border placeholder:text-muted-foreground/40 focus-visible:ring-ring w-full rounded-md border bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2'

const CEO_IMAGE_OPTIONS = [
  { id: 'desk', label: '책상', src: '/assets/agents/ceo/ceo_desk.png' },
  { id: 'explain', label: '설명', src: '/assets/agents/ceo/ceo_explain.png' },
  { id: 'profile', label: '프로필', src: '/assets/agents/ceo/ceo_profile.png' },
] as const

const MAIN_AGENT_SKILL_OPTIONS = [
  { id: 'notion', label: 'Notion', description: '문서와 데이터베이스를 정리합니다.' },
  {
    id: 'samsung-health',
    label: 'Samsung Health',
    description: '건강 기록과 루틴 맥락을 확인합니다.',
  },
  { id: 'code', label: 'Code', description: '코드 읽기와 구현 작업을 맡습니다.' },
] as const

function MainAgentHeader({
  callName,
  model,
  name,
  onConfigure,
  profileImage,
  saved,
  saving,
}: {
  callName: string
  model: string
  name: string
  onConfigure: () => void
  profileImage: string
  saved: boolean
  saving: boolean
}) {
  return (
    <AgentDetailHeader
      name={name}
      status="작업 가능"
      subtitle={
        <>
          {callName} · {model || '기본 모델'}
        </>
      }
      profile={
        <button
          type="button"
          onClick={onConfigure}
          className="bg-accent hover:bg-accent/80 flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
          aria-label="메인 에이전트 프로필 설정 열기"
        >
          <img src={profileImage} alt="" className="h-10 w-10 object-contain" draggable={false} />
        </button>
      }
      savedIndicator={
        <>
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
        </>
      }
    />
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

function normalizeMainAgentSkillIds(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const allowed = new Set<string>(MAIN_AGENT_SKILL_OPTIONS.map((skill) => skill.id))
  return Array.from(
    new Set(value.filter((item): item is string => typeof item === 'string' && allowed.has(item))),
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
  onFamilySelect,
}: {
  effectiveSelectedFamily: ModelFamily
  modelFamilies: Array<{ id: ModelFamily; label: string }>
  onFamilySelect: (family: ModelFamily) => void
}) {
  return (
    <div className="space-y-3">
      <Field label="연결 방식">
        <AgentAdapterTypeDropdown
          value={effectiveSelectedFamily}
          options={modelFamilies.map((family) => ({
            value: family.id,
            label: family.id === 'gpt' ? 'OpenAI API' : family.label,
          }))}
          onChange={(value) => onFamilySelect(value as ModelFamily)}
        />
      </Field>
    </div>
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
    <div
      className="flex min-h-36 w-full min-w-0 items-center justify-center gap-5 rounded-lg"
      aria-label="에이전트 이미지"
    >
      <button
        type="button"
        onClick={() => {
          const nextIndex =
            (selectedImageIndex - 1 + CEO_IMAGE_OPTIONS.length) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
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
        className="bg-accent hover:bg-accent/80 flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
        aria-label={`${selectedImage?.label ?? '메인 에이전트'} 이미지 변경`}
      >
        <img src={profileImage} alt="" className="h-24 w-24 object-contain" draggable={false} />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="다음 에이전트 이미지"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
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
