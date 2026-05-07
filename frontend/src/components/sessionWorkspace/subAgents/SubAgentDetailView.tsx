import { useState } from 'react'
import { Activity, BarChart3, Clock, FileText } from 'lucide-react'
import { PageTabBar } from '@/components/PageTabBar'
import {
  AgentBudgetPanel,
  AgentConfigurationPanel,
  AgentDashboardPanel,
  AgentDetailHeader,
  AgentInstructionsBundlePanel,
  AgentInstructionsPanel,
  AgentRunsPanel,
  AgentSkillsLibraryPanel,
  AgentSkillsPanel,
} from '@/components/sessionWorkspace/AgentDetailPanels'
import { Button } from '@/components/ui/button'
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
  { value: 'dashboard', label: '대시보드' },
  { value: 'instructions', label: '지침' },
  { value: 'skills', label: '스킬' },
  { value: 'configuration', label: '설정' },
  { value: 'runs', label: '실행 기록' },
  { value: 'budget', label: '예산' },
]

export function SubAgentDetailView({
  item,
  onSave,
  onTabChange,
  reservedNames,
  requestedTab,
}: {
  item: AgentPanelItem
  onSave: (agent: Agent) => void
  onTabChange?: (tab: SubAgentDetailTab) => void
  requestedTab?: string | null
  reservedNames: string[]
}) {
  const [tab, setTab] = useState<SubAgentDetailTab>(getDetailTab(requestedTab))
  const [instructionsDraft, setInstructionsDraft] = useState(item.agent.instructions ?? '')
  const [instructionsEntryFile, setInstructionsEntryFile] = useState(
    item.agent.instructionsEntryFile ?? 'AGENTS.md',
  )
  const [instructionsFiles, setInstructionsFiles] = useState(item.agent.instructionsFiles ?? {})
  const [instructionsMode, setInstructionsMode] = useState<'managed' | 'external'>(
    item.agent.instructionsMode ?? 'managed',
  )
  const [instructionsRootPath, setInstructionsRootPath] = useState(
    item.agent.instructionsRootPath ?? '',
  )
  const [skillSaving, setSkillSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const selectedSkills = SUB_AGENT_SKILLS.filter((skill) => item.agent.skills?.includes(skill.id))
  const instructionsDirty =
    instructionsDraft.trim() !== (item.agent.instructions ?? '') ||
    instructionsEntryFile.trim() !== (item.agent.instructionsEntryFile ?? 'AGENTS.md') ||
    !shallowStringRecordEqual(instructionsFiles, item.agent.instructionsFiles ?? {}) ||
    instructionsMode !== (item.agent.instructionsMode ?? 'managed') ||
    instructionsRootPath.trim() !== (item.agent.instructionsRootPath ?? '')

  const selectTab = (nextTab: SubAgentDetailTab) => {
    setTab(nextTab)
    onTabChange?.(nextTab)
    setSaved(false)
  }

  const resetInstructionsDraft = () => {
    setInstructionsDraft(item.agent.instructions ?? '')
    setInstructionsEntryFile(item.agent.instructionsEntryFile ?? 'AGENTS.md')
    setInstructionsFiles(item.agent.instructionsFiles ?? {})
    setInstructionsMode(item.agent.instructionsMode ?? 'managed')
    setInstructionsRootPath(item.agent.instructionsRootPath ?? '')
    setSaved(false)
  }

  const saveInstructionsDraft = () => {
    if (!instructionsDirty) return
    onSave({
      ...item.agent,
      instructions: instructionsDraft.trim(),
      instructionsEntryFile: instructionsEntryFile.trim() || 'AGENTS.md',
      instructionsFiles,
      instructionsMode,
      instructionsRootPath: instructionsRootPath.trim(),
    })
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1400)
  }

  const toggleSkill = (skillId: string, checked: boolean) => {
    const currentSkills = item.agent.skills ?? []
    const nextSkills = checked
      ? Array.from(new Set([...currentSkills, skillId]))
      : currentSkills.filter((id) => id !== skillId)
    setSkillSaving(true)
    onSave({ ...item.agent, skills: nextSkills })
    window.setTimeout(() => setSkillSaving(false), 500)
  }

  return (
    <div className={`space-y-6 ${instructionsDirty ? 'pb-24 sm:pb-0' : ''}`}>
      <AgentDetailHeader
        name={item.agent.name}
        onInstructions={() => selectTab('instructions')}
        onRuns={() => selectTab('runs')}
        status="draft"
        subtitle={
          <>
            {item.agent.role ?? 'general'}
            {item.agent.title ? ` · ${item.agent.title}` : ''}
          </>
        }
        profile={
          <button
            type="button"
            onClick={() => selectTab('configuration')}
            className="rounded-lg transition-opacity hover:opacity-80"
            aria-label="서브 에이전트 프로필 설정 열기"
          >
            <SubAgentProfileImage
              accent={item.agent.accent}
              profileImage={item.agent.profileImage}
              spriteId={item.agent.spriteId}
              size="large"
            />
          </button>
        }
        savedIndicator={
          saved ? <span className="text-xs font-medium text-emerald-600">저장됨</span> : undefined
        }
      />

      <Tabs value={tab} onValueChange={(next) => selectTab(next as SubAgentDetailTab)}>
        <PageTabBar
          align="start"
          items={DETAIL_TABS}
          value={tab}
          onValueChange={(next) => selectTab(next as SubAgentDetailTab)}
        />
      </Tabs>

      {tab === 'dashboard' && (
        <AgentDashboardPanel
          costs={[
            { label: '입력 토큰', value: '0' },
            { label: '출력 토큰', value: '0' },
            { label: '캐시 토큰', value: '0' },
            { label: '총 비용', value: '$0.00' },
          ]}
          latestRun={null}
          metrics={[
            {
              icon: Activity,
              label: '실행 현황',
              value: '초안',
              description: '최근 14일',
            },
            {
              icon: FileText,
              label: '우선순위별 이슈',
              value: '0',
              description: '최근 14일',
            },
            {
              icon: BarChart3,
              label: '상태별 이슈',
              value: '0',
              description: '최근 14일',
            },
            {
              icon: Clock,
              label: '성공률',
              value: '0',
              description: '최근 14일',
            },
          ]}
          recentTitle="최근 이슈"
          recentEmptyText="최근 이슈가 없습니다."
          recentItems={[]}
        />
      )}

      <div className={tab === 'configuration' ? '' : 'hidden'}>
        <AgentConfigurationPanel>
          <SubAgentDraftForm
            key={item.id}
            initialAgent={item.agent}
            onCancel={() => selectTab('dashboard')}
            onSave={onSave}
            reservedNames={reservedNames}
          />
        </AgentConfigurationPanel>
      </div>

      <div className={tab === 'instructions' ? '' : 'hidden'}>
        <AgentInstructionsPanel>
          <AgentInstructionsBundlePanel
            content={instructionsDraft}
            entryFile={instructionsEntryFile}
            files={instructionsFiles}
            mode={instructionsMode}
            rootPath={instructionsRootPath}
            onContentChange={(value) => {
              setInstructionsDraft(value)
              setSaved(false)
            }}
            onEntryFileChange={(value) => {
              setInstructionsEntryFile(value)
              setSaved(false)
            }}
            onFilesChange={(value) => {
              setInstructionsFiles(value)
              setSaved(false)
            }}
            onModeChange={(value) => {
              setInstructionsMode(value)
              setSaved(false)
            }}
            onRootPathChange={(value) => {
              setInstructionsRootPath(value)
              setSaved(false)
            }}
          />
        </AgentInstructionsPanel>
      </div>

      {tab === 'skills' && (
        <AgentSkillsPanel>
          <AgentSkillsLibraryPanel
            adapterLabel={item.agent.adapterType ?? 'local'}
            applicationLabel="에이전트 실행 시 적용"
            rows={SUB_AGENT_SKILLS.map((skill) => ({
              key: skill.id,
              name: skill.label,
              description: skill.description,
              checked: item.agent.skills?.includes(skill.id) ?? false,
              linkLabel: '보기',
            }))}
            selectedCount={selectedSkills.length}
            saving={skillSaving}
            onSkillToggle={toggleSkill}
          />
        </AgentSkillsPanel>
      )}

      {tab === 'runs' && <AgentRunsPanel emptyText="아직 실행 기록이 없습니다." items={[]} />}

      {tab === 'budget' && (
        <AgentBudgetPanel
          summary={{
            amountLabel: '사용 안 함',
            observedLabel: '$0.00',
            remainingLabel: '제한 없음',
            scopeName: item.agent.name,
            scopeType: '에이전트',
            status: 'healthy',
            utilizationPercent: 0,
            warnPercent: 80,
            windowLabel: '월간 예산',
          }}
        />
      )}

      {instructionsDirty && (
        <div className="border-border bg-background/95 fixed inset-x-0 bottom-0 z-30 border-t backdrop-blur-sm sm:hidden">
          <div className="flex items-center justify-end gap-2 px-3 py-2 pb-[max(env(safe-area-inset-bottom),0.5rem)]">
            <Button variant="ghost" size="sm" onClick={resetInstructionsDraft}>
              취소
            </Button>
            <Button size="sm" onClick={saveInstructionsDraft}>
              저장
            </Button>
          </div>
        </div>
      )}
      {instructionsDirty && (
        <div className="fixed right-6 bottom-6 z-30 hidden sm:block">
          <div className="bg-background/90 border-border flex items-center gap-2 rounded-lg border px-3 py-1.5 shadow-lg backdrop-blur-sm">
            <Button variant="ghost" size="sm" onClick={resetInstructionsDraft}>
              취소
            </Button>
            <Button size="sm" onClick={saveInstructionsDraft}>
              저장
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function getDetailTab(value: string | null | undefined): SubAgentDetailTab {
  return DETAIL_TABS.some((tab) => tab.value === value) ? (value as SubAgentDetailTab) : 'dashboard'
}

function shallowStringRecordEqual(left: Record<string, string>, right: Record<string, string>) {
  const leftEntries = Object.entries(left)
  const rightEntries = Object.entries(right)
  if (leftEntries.length !== rightEntries.length) return false
  return leftEntries.every(([key, value]) => right[key] === value)
}
