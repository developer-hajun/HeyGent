import { useSearchParams } from 'react-router'
import { useSessionStore } from '@/store/useSessionStore'
import { SubAgentCreateDialog } from './SubAgentCreateDialog'
import { SubAgentDraftForm } from './SubAgentDraftForm'
import { SubAgentDetailView } from './SubAgentDetailView'
import { SubAgentList } from './SubAgentList'
import { SubAgentsPanelShell } from './SubAgentsPanelShell'
import { normalizeSubAgentAdapterType } from './subAgentConfigOptions'

export function SubAgentsPanel({ sessionId }: { sessionId: string }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const { addAgentPanelToSession, getAgentPanelsForSession, updateAgentPanelInSession } =
    useSessionStore()
  const agentPanels = getAgentPanelsForSession(sessionId)
  const detailId = searchParams.get('agent')
  const createDialogOpen = searchParams.get('create') === '1'
  const initialAdapterType = normalizeSubAgentAdapterType(
    searchParams.get('adapterType') ?? undefined,
  )
  const detailItem =
    detailId === null ? undefined : agentPanels.find((panel) => panel.id === detailId)
  const draftMode = searchParams.get('new') === '1'

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
            addAgentPanelToSession(sessionId, agent)
            resetDraft()
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
          key={detailItem.id}
          item={detailItem}
          onSave={(agent) => updateAgentPanelInSession(sessionId, detailItem.id, agent)}
          onTabChange={(tab) => openDetailTab(detailItem.id, tab)}
          requestedTab={searchParams.get('subAgentTab')}
          reservedNames={agentPanels
            .filter((item) => item.id !== detailItem.id)
            .map((item) => item.agent.name)}
        />
      </SubAgentsPanelShell>
    )
  }

  return (
    <SubAgentsPanelShell title="에이전트" description="세션 에이전트 설정">
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
          resetDraft()
        }}
        onPickAdapter={(adapterType) => {
          setSearchParams({ new: '1', adapterType })
        }}
      />
    </SubAgentsPanelShell>
  )
}
