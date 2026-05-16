import { useSearchParams } from 'react-router'
import { useEffect, useState } from 'react'
import {
  agentProfilesToPanelItems,
  createDefaultSessionAgents,
  createSessionAgent,
  createSessionAgentFromTemplate,
  deleteSessionAgent,
  updateSessionAgent,
  listAgentTemplates,
  listSessionAgents,
  type AgentTemplate,
  agentProfileToAgent,
} from '@/apis/agents'
import { useSessionStore } from '@/store/useSessionStore'
import { SubAgentCreateDialog } from './SubAgentCreateDialog'
import { SubAgentDraftForm } from './SubAgentDraftForm'
import { SubAgentDetailView } from './SubAgentDetailView'
import { SubAgentList } from './SubAgentList'
import { SubAgentsPanelShell } from './SubAgentsPanelShell'
import { normalizeSubAgentAdapterType } from './subAgentConfigOptions'

export function SubAgentsPanel({ sessionId }: { sessionId: string }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const {
    getAgentPanelsForSession,
    removeAgentPanelFromSession,
    setAgentPanelsForSession,
    updateAgentPanelInSession,
  } = useSessionStore()
  const agentPanels = getAgentPanelsForSession(sessionId)
  const detailId = searchParams.get('agent')
  const createDialogOpen = searchParams.get('create') === '1'
  const initialAdapterType = normalizeSubAgentAdapterType(
    searchParams.get('adapterType') ?? undefined,
  )
  const detailItem =
    detailId === null ? undefined : agentPanels.find((panel) => panel.id === detailId)
  const draftMode = searchParams.get('new') === '1'

  useEffect(() => {
    let alive = true
    void Promise.all([listAgentTemplates(), listSessionAgents(sessionId)])
      .then(([nextTemplates, profiles]) => {
        if (!alive) return
        setTemplates(nextTemplates)
        setAgentPanelsForSession(sessionId, agentProfilesToPanelItems(profiles))
        setLoadError(null)
      })
      .catch((error) => {
        if (!alive) return
        setLoadError(error instanceof Error ? error.message : '에이전트를 불러오지 못했습니다.')
      })
    return () => {
      alive = false
    }
  }, [sessionId, setAgentPanelsForSession])

  const resetDraft = () => {
    setSearchParams({})
  }

  const openDetail = (itemId: string) => {
    setSearchParams({ agent: itemId })
  }

  const openDetailTab = (itemId: string, tab: string) => {
    if (tab === 'dashboard') {
      setSearchParams({ agent: itemId })
      return
    }
    setSearchParams({ agent: itemId, subAgentTab: tab })
  }

  const openCreateDraft = () => {
    setSearchParams({ create: '1' })
  }

  if (draftMode) {
    return (
      <SubAgentsPanelShell title="새 에이전트" description="세부 설정">
        <SubAgentDraftForm
          key="create"
          initialAdapterType={initialAdapterType}
          onCancel={resetDraft}
          reservedNames={agentPanels.map((item) => item.agent.name)}
          onSave={(agent) => {
            void createSessionAgent(sessionId, {
              name: agent.name,
              role: agent.role ?? 'general',
              title: agent.title,
              description: agent.description,
              adapterType: agent.adapterType,
              model: agent.model,
              profileImage: agent.profileImage,
              skills: agent.skills,
              entryDocumentKey: agent.instructionsEntryFile ?? 'AGENTS.md',
              instructionsFiles: agent.instructionsFiles ?? {
                [agent.instructionsEntryFile ?? 'AGENTS.md']: agent.instructions ?? '',
              },
            })
              .then(() => listSessionAgents(sessionId))
              .then((profiles) => {
                setAgentPanelsForSession(sessionId, agentProfilesToPanelItems(profiles))
                resetDraft()
              })
              .catch((error) => {
                setLoadError(
                  error instanceof Error ? error.message : '에이전트를 저장하지 못했습니다.',
                )
              })
          }}
        />
      </SubAgentsPanelShell>
    )
  }

  if (detailItem !== undefined) {
    return (
      <SubAgentsPanelShell
        title={detailItem.agent.name}
        description={detailItem.agent.title || '에이전트 상세'}
        hideHeader
        width="wide"
      >
        <SubAgentDetailView
          key={`${sessionId}:${detailItem.id}`}
          item={detailItem}
          onDelete={async () => {
            await deleteSessionAgent(sessionId, detailItem.id)
            removeAgentPanelFromSession(sessionId, detailItem.id)
            resetDraft()
          }}
          onSave={(agent) => {
            const documentKey = agent.instructionsEntryFile ?? 'AGENTS.md'
            // 옵티미스틱: 사이드바·상세 헤더(이름/호칭 등)가 즉시 새 값으로 보이도록 패치 먼저.
            const previousAgent = detailItem.agent
            const optimisticAgent = { ...previousAgent, ...agent }
            updateAgentPanelInSession(sessionId, detailItem.id, optimisticAgent)
            void updateSessionAgent(sessionId, detailItem.id, {
              name: agent.name,
              role: agent.role ?? 'general',
              title: agent.title,
              description: agent.description,
              adapterType: agent.adapterType,
              model: agent.model,
              profileImage: agent.profileImage,
              skills: agent.skills,
              entryDocumentKey: documentKey,
              instructionsFiles: agent.instructionsFiles ?? {
                [documentKey]: agent.instructions ?? '',
              },
            })
              .then((profile) => {
                // 서버 응답으로 정식 값을 한 번 더 적용한다. 단, 서버가 일부 필드를 null/빈 값으로
                // 내려주는 경우 사용자가 방금 입력한 옵티미스틱 값(특히 호칭·이름)을 덮어쓰지 않도록
                // 보호한다.
                const serverAgent = agentProfileToAgent(profile)
                updateAgentPanelInSession(sessionId, detailItem.id, {
                  ...serverAgent,
                  name: serverAgent.name?.trim() ? serverAgent.name : optimisticAgent.name,
                  title: serverAgent.title?.trim() ? serverAgent.title : optimisticAgent.title,
                  description:
                    serverAgent.description !== undefined && serverAgent.description !== ''
                      ? serverAgent.description
                      : optimisticAgent.description,
                })
              })
              .catch((error) => {
                // 실패 시 옵티미스틱 패치를 이전 상태로 롤백
                updateAgentPanelInSession(sessionId, detailItem.id, previousAgent)
                setLoadError(
                  error instanceof Error ? error.message : '에이전트를 저장하지 못했습니다.',
                )
              })
          }}
          onTabChange={(tab) => openDetailTab(detailItem.id, tab)}
          requestedTab={searchParams.get('subAgentTab')}
          reservedNames={agentPanels
            .filter((item) => item.id !== detailItem.id)
            .map((item) => item.agent.name)}
          sessionId={sessionId}
        />
      </SubAgentsPanelShell>
    )
  }

  return (
    <SubAgentsPanelShell title="에이전트" description="세션 에이전트 설정">
      {loadError && (
        <p className="text-destructive border-destructive/30 mb-3 rounded-md border px-3 py-2 text-xs">
          {loadError}
        </p>
      )}
      <SubAgentList agentPanels={agentPanels} onCreate={openCreateDraft} onOpen={openDetail} />
      <SubAgentCreateDialog
        open={createDialogOpen}
        onOpenChange={(open) => {
          if (open) {
            setSearchParams({ create: '1' })
          } else {
            resetDraft()
          }
        }}
        onAskCeo={() => {
          void createDefaultSessionAgents(sessionId)
            .then((profiles) => {
              setAgentPanelsForSession(sessionId, agentProfilesToPanelItems(profiles))
              resetDraft()
            })
            .catch((error) => {
              setLoadError(
                error instanceof Error ? error.message : '기본 에이전트를 만들지 못했습니다.',
              )
            })
        }}
        onPickAdapter={(adapterType) => {
          setSearchParams({ new: '1', adapterType })
        }}
        onPickTemplate={(templateId) => {
          void createSessionAgentFromTemplate(sessionId, templateId)
            .then(() => listSessionAgents(sessionId))
            .then((profiles) => {
              setAgentPanelsForSession(sessionId, agentProfilesToPanelItems(profiles))
              resetDraft()
            })
            .catch((error) => {
              setLoadError(error instanceof Error ? error.message : '에이전트를 만들지 못했습니다.')
            })
        }}
        templates={templates}
      />
    </SubAgentsPanelShell>
  )
}
