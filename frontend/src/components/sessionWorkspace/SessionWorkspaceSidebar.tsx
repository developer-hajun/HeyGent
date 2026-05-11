import { useEffect } from 'react'
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
import { agentProfilesToPanelItems, listSessionAgents } from '@/apis/agents'

export function SessionWorkspaceSidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const sessionWorkspaceCollapsed = useUIStore((state) => state.sessionWorkspaceCollapsed)
  const setSidebarCollapsed = useUIStore((state) => state.setSidebarCollapsed)
  const setSessionWorkspaceCollapsed = useUIStore((state) => state.setSessionWorkspaceCollapsed)
  const setSelectedSessionId = useSessionStore((state) => state.setSelectedSessionId)
  const setAgentPanelsForSession = useSessionStore((state) => state.setAgentPanelsForSession)
  const sessionsById = useChatStore((state) => state.sessionsById)
  const deleteSession = useChatStore((state) => state.deleteSession)
  const connectionStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const accessToken = useAuthStore((state) => state.accessToken)
  const sessionId = getCurrentWorkspaceSessionId(location.pathname)
  const activePanel = getWorkspacePanelFromPath(location.pathname)
  const session = sessionId === null ? null : (sessionsById[sessionId] ?? null)
  const currentRoute = location.pathname.startsWith('/agent-status/') ? 'visualization' : 'chat'
  const searchParams = new URLSearchParams(location.search)
  const activeSubAgentId = searchParams.get('agent')
  const connectionState = getWorkspaceConnectionState(
    connectionStatus,
    authStatus,
    accessToken,
    realtimeError,
  )

  useEffect(() => {
    if (sessionId === null || accessToken === null) return
    if (sessionId.startsWith('pending_session_')) return

    let cancelled = false
    void listSessionAgents(sessionId)
      .then((profiles) => {
        if (cancelled) return
        setAgentPanelsForSession(sessionId, agentProfilesToPanelItems(profiles))
      })
      .catch(() => {
        // 세션 확정 전 pending 경로에서는 서버 세션이 아직 없을 수 있다.
      })

    return () => {
      cancelled = true
    }
  }, [accessToken, sessionId, setAgentPanelsForSession])

  if (sessionId === null) {
    return null
  }

  const handleSelectPanel = (panelId: WorkspaceNavId) => {
    if (panelId === 'chat') {
      setSelectedSessionId(sessionId)
      setSidebarCollapsed(true)
      navigate(`/session/${sessionId}`)
      return
    }

    setSelectedSessionId(sessionId)
    navigate(getWorkspacePanelPath(sessionId, panelId))
  }

  const handleCreateSubAgent = () => {
    setSelectedSessionId(sessionId)
    navigate(`${getWorkspacePanelPath(sessionId, 'subAgents')}?create=1`)
  }

  const handleOpenSubAgent = (agentPanelId: string) => {
    setSelectedSessionId(sessionId)
    navigate(
      `${getWorkspacePanelPath(sessionId, 'subAgents')}?agent=${encodeURIComponent(agentPanelId)}`,
    )
  }

  const handleDeleteSession = async () => {
    await deleteSession(sessionId)
    setSelectedSessionId(null)
    navigate('/new-chat', { replace: true })
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
      onDeleteSession={handleDeleteSession}
      onOpenSubAgent={handleOpenSubAgent}
      onSelectPanel={handleSelectPanel}
    />
  )
}
