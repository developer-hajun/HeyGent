import { useLocation, useNavigate } from 'react-router'
import { SessionWorkspaceMenu } from './SessionWorkspaceMenu'
import {
  getCurrentWorkspaceSessionId,
  getWorkspaceConnectionState,
  getWorkspacePanelFromPath,
  getWorkspacePanelPath,
} from './sessionWorkspaceUtils'
import type { WorkspaceNavId } from './sessionWorkspaceTypes'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useUIStore } from '@/store/useUIStore'

export function SessionWorkspaceSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const sessionWorkspaceCollapsed = useUIStore((state) => state.sessionWorkspaceCollapsed)
  const setSessionWorkspaceCollapsed = useUIStore((state) => state.setSessionWorkspaceCollapsed)
  const setSelectedSessionId = useSessionStore((state) => state.setSelectedSessionId)
  const sessionsById = useChatStore((state) => state.sessionsById)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const accessToken = useAuthStore((state) => state.accessToken)
  const sessionId = getCurrentWorkspaceSessionId(location.pathname)
  const activePanel = getWorkspacePanelFromPath(location.pathname)
  const session = sessionId === null ? null : (sessionsById[sessionId] ?? null)
  const currentRoute = location.pathname.startsWith('/agent-status/') ? 'visualization' : 'chat'
  const activeSubAgentId = new URLSearchParams(location.search).get('edit')
  const connectionState = getWorkspaceConnectionState(
    connectionStatus,
    authStatus,
    accessToken,
    realtimeError,
  )

  if (sessionId === null) {
    return null
  }

  const handleSelectPanel = (panelId: WorkspaceNavId) => {
    if (panelId === 'chat') {
      setSelectedSessionId(sessionId)
      navigate(`/session/${sessionId}`)
      return
    }

    setSelectedSessionId(sessionId)
    navigate(getWorkspacePanelPath(sessionId, panelId))
  }

  const handleCreateSubAgent = () => {
    setSelectedSessionId(sessionId)
    navigate(`${getWorkspacePanelPath(sessionId, 'subAgents')}?new=1`)
  }

  const handleEditSubAgent = (agentPanelId: string) => {
    setSelectedSessionId(sessionId)
    navigate(
      `${getWorkspacePanelPath(sessionId, 'subAgents')}?edit=${encodeURIComponent(agentPanelId)}`,
    )
  }

  return (
    <SessionWorkspaceMenu
      key={sessionId}
      activePanel={activePanel}
      collapsed={sessionWorkspaceCollapsed}
      connectionState={connectionState}
      currentRoute={currentRoute}
      session={session}
      sessionId={sessionId}
      activeSubAgentId={activeSubAgentId}
      onCollapsedChange={setSessionWorkspaceCollapsed}
      onCreateSubAgent={handleCreateSubAgent}
      onEditSubAgent={handleEditSubAgent}
      onSelectPanel={handleSelectPanel}
    />
  )
}
