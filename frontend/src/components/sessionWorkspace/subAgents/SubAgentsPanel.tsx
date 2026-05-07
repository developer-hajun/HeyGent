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
  const {
    addAgentPanelToSession,
    getAgentPanelsForSession,
    removeAgentPanelFromSession,
    updateAgentPanelInSession,
  } = useSessionStore()
  const agentPanels = getAgentPanelsForSession(sessionId)
  const editingId = searchParams.get('edit')
  const detailId = searchParams.get('agent')
  const createDialogOpen = searchParams.get('create') === '1'
  const initialAdapterType = normalizeSubAgentAdapterType(
    searchParams.get('adapterType') ?? undefined,
  )
  const editingItem =
    editingId === null ? undefined : agentPanels.find((panel) => panel.id === editingId)
  const detailItem =
    detailId === null ? undefined : agentPanels.find((panel) => panel.id === detailId)
  const draftMode =
    searchParams.get('new') === '1' ? 'create' : editingItem !== undefined ? 'edit' : null

  const resetDraft = () => {
    setSearchParams({})
  }

  const openEditDraft = (itemId: string) => {
    setSearchParams({ agent: itemId, subAgentTab: 'configuration' })
  }

  const openDetail = (itemId: string) => {
    setSearchParams({ agent: itemId })
  }

  const openCreateDraft = () => {
    setSearchParams({ create: '1' })
  }

  if (draftMode !== null) {
    return (
      <SubAgentsPanelShell
        title={draftMode === 'edit' ? 'Edit Agent' : 'New Agent'}
        description="Advanced agent configuration"
      >
        <SubAgentDraftForm
          key={draftMode === 'edit' ? editingItem?.id : 'create'}
          initialAdapterType={initialAdapterType}
          initialAgent={draftMode === 'edit' ? editingItem?.agent : undefined}
          onCancel={resetDraft}
          reservedNames={agentPanels
            .filter((item) => item.id !== editingItem?.id)
            .map((item) => item.agent.name)}
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
      </SubAgentsPanelShell>
    )
  }

  if (detailItem !== undefined) {
    return (
      <SubAgentsPanelShell
        title={detailItem.agent.name}
        description={detailItem.agent.title || 'Agent detail'}
        hideHeader
        width="wide"
      >
        <SubAgentDetailView
          key={`${detailItem.id}:${searchParams.get('subAgentTab') ?? 'dashboard'}`}
          item={detailItem}
          onSave={(agent) => updateAgentPanelInSession(sessionId, detailItem.id, agent)}
          requestedTab={searchParams.get('subAgentTab')}
          reservedNames={agentPanels
            .filter((item) => item.id !== detailItem.id)
            .map((item) => item.agent.name)}
        />
      </SubAgentsPanelShell>
    )
  }

  return (
    <SubAgentsPanelShell title="Agents" description="Session agent configuration">
      <SubAgentList
        agentPanels={agentPanels}
        onCreate={openCreateDraft}
        onEdit={openEditDraft}
        onOpen={openDetail}
        onRemove={(itemId) => removeAgentPanelFromSession(sessionId, itemId)}
      />
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
