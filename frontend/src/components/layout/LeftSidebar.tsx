import { useRef, useCallback, useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router'
import {
  Activity,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
  LayoutDashboard,
  MessageCircle,
  MessageSquare,
  Clock,
  GripVertical,
  Moon,
  PanelRightOpen,
  Plus,
  User,
  Settings,
  Sun,
  LogOut,
  UserCircle,
  Wifi,
  X,
  Edit3,
  MoreHorizontal,
  Pin,
  PinOff,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SettingsDialog } from '@/components/SettingsDialog'
import { NewSessionModal, type CustomAgentConfig } from '@/components/session/NewSessionModal'
import { SessionSettingsModal } from '@/components/session/SessionSettingsModal'
import { useUIStore } from '@/store/useUIStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useAuthStore } from '@/store/useAuthStore'
import { useAiRealtimeStore } from '@/store/useAiRealtimeStore'
import { useChatStore } from '@/store/useChatStore'
import { logout } from '@/apis/auth'
import { updateMyInfo } from '@/apis/users'
import type { RawAiSession } from '@/types/aiChat'

type SidebarSession = {
  id: string
  title: string
  preview: string
  time: string
  isRunning: boolean
  raw: RawAiSession
}

type SessionConfirmAction = 'delete'
type SidebarConnectionState = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'error'

type SessionConfirmState = {
  sessionId: string
  action: SessionConfirmAction
}

export function LeftSidebar() {
  const {
    sidebarCollapsed: collapsed,
    sidebarWidth: width,
    settingsOpen,
    settingsInitialTab,
    theme,
    setSidebarCollapsed,
    clampSidebarWidth,
    setSettingsOpen,
    setTheme,
    setTaskActivityPanelOpen,
  } = useUIStore()
  const { selectedSessionId, setSelectedSessionId, pinnedSessionIds, togglePinSession } =
    useSessionStore()
  const [profileOpen, setProfileOpen] = useState(false)
  const [sessionsPopoverOpen, setSessionsPopoverOpen] = useState(false)
  const [newSessionModalOpen, setNewSessionModalOpen] = useState(false)
  const [sessionSettingsSessionId, setSessionSettingsSessionId] = useState<string | null>(null)
  const [sessionConfirm, setSessionConfirm] = useState<SessionConfirmState | null>(null)
  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const realtimeStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const authStatus = useAiRealtimeStore((state) => state.authStatus)
  const realtimeError = useAiRealtimeStore((state) => state.lastError)
  const accessToken = useAuthStore((state) => state.accessToken)
  const sessionsById = useChatStore((state) => state.sessionsById)
  const sessionListLoading = useChatStore((state) => state.sessionListLoading)
  const chatError = useChatStore((state) => state.sessionListError ?? state.lastError)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const deleteSession = useChatStore((state) => state.deleteSession)
  const isResizing = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)
  const navigate = useNavigate()
  const location = useLocation()
  const currentChatSessionId = getCurrentChatSessionId(location.pathname)
  const sidebarSessions = useMemo(() => {
    const all = Object.values(sessionsById)
      .map(toSidebarSession)
      .filter((s) => !isRemovedSidebarSession(s.raw))
      .sort((first, second) => getSessionTime(second.raw) - getSessionTime(first.raw))
    const pinned = all.filter((s) => pinnedSessionIds.has(s.id))
    const unpinned = all.filter((s) => !pinnedSessionIds.has(s.id))
    return [...pinned, ...unpinned]
  }, [sessionsById, pinnedSessionIds])
  const runningSessions = useMemo(
    () => sidebarSessions.filter((session) => session.isRunning),
    [sidebarSessions],
  )
  const sessionSettingsSession =
    sessionSettingsSessionId === null ? null : (sessionsById[sessionSettingsSessionId] ?? null)
  const currentChatSession =
    currentChatSessionId === null ? null : (sessionsById[currentChatSessionId] ?? null)
  const currentChatTitle = useMemo(
    () => getSessionDisplayName(currentChatSession),
    [currentChatSession],
  )
  const connectionState = getSidebarConnectionState(
    realtimeStatus,
    authStatus,
    accessToken,
    realtimeError,
  )

  useEffect(() => {
    if (commandClient === null) {
      return
    }

    void fetchSessions().catch(() => undefined)
  }, [commandClient, fetchSessions])

  const handleNewChat = () => {
    setNewSessionModalOpen(true)
  }

  const handleOpenChatSession = (sessionId: string, event?: React.MouseEvent) => {
    event?.stopPropagation()
    navigate(`/session/${sessionId}`)
  }

  const handleConfirmSessionAction = async () => {
    if (sessionConfirm === null) {
      return
    }

    const { sessionId, action } = sessionConfirm
    try {
      if (action === 'delete') {
        await deleteSession(sessionId)
      }

      if (location.pathname === `/session/${sessionId}`) {
        navigate('/new-chat')
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '세션 작업에 실패했습니다.')
    } finally {
      setSessionConfirm(null)
    }
  }

  const startResize = useCallback(
    (e: React.MouseEvent) => {
      isResizing.current = true
      startX.current = e.clientX
      startWidth.current = width
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      e.preventDefault()
    },
    [width],
  )

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return
      const delta = e.clientX - startX.current
      clampSidebarWidth(startWidth.current + delta)
    }
    const handleMouseUp = () => {
      if (!isResizing.current) return
      isResizing.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [clampSidebarWidth])

  return (
    <>
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        sessionId={
          location.pathname.startsWith('/session/') ? location.pathname.slice(9) : undefined
        }
        initialTab={settingsInitialTab as 'apiKeys'}
      />
      <NewSessionModal
        open={newSessionModalOpen}
        onOpenChange={setNewSessionModalOpen}
        onConfirm={(config) => {
          storePendingSessionConfig(config)
          setNewSessionModalOpen(false)
          if (config) {
            navigate('/agent-status')
          } else {
            navigate('/new-chat')
          }
        }}
      />
      <SessionSettingsModal
        open={sessionSettingsSessionId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSessionSettingsSessionId(null)
          }
        }}
        session={sessionSettingsSession}
      />
      {sessionConfirm !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-card border-border w-80 rounded-2xl border p-6 shadow-xl">
            <h3 className="text-foreground mb-2 text-base font-semibold">
              {getSessionConfirmTitle(sessionConfirm.action)}
            </h3>
            <p className="text-muted-foreground mb-5 text-sm">
              {getSessionConfirmMessage(sessionConfirm.action)}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setSessionConfirm(null)}
                className="bg-muted text-foreground hover:bg-muted/80 flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                취소
              </button>
              <button
                onClick={() => void handleConfirmSessionAction()}
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors ${
                  sessionConfirm.action === 'delete'
                    ? 'bg-red-500 hover:bg-red-600'
                    : 'bg-primary hover:bg-primary/90'
                }`}
              >
                {getSessionConfirmButtonLabel(sessionConfirm.action)}
              </button>
            </div>
          </div>
        </div>
      )}

      <div
        className="bg-sidebar border-sidebar-border relative flex shrink-0 flex-col overflow-hidden border-r transition-[width] duration-200 ease-in-out"
        style={{ width: collapsed ? 52 : width }}
      >
        {/* ── Collapsed Rail ── */}
        {collapsed && (
          <div className="flex h-full flex-col items-center gap-1 py-3">
            <CollapsedTooltip label="홈">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="hover:bg-sidebar-accent flex h-10 w-10 items-center justify-center rounded-lg transition-colors"
                aria-label="홈으로 이동"
              >
                <img
                  src="/logo-sidebar.png"
                  alt="HeyGent"
                  className="h-9 w-9 rounded-md object-contain"
                />
              </button>
            </CollapsedTooltip>

            {/* Expand button */}
            <CollapsedTooltip label="사이드바 열기">
              <button
                type="button"
                onClick={() => setSidebarCollapsed(false)}
                className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </CollapsedTooltip>

            <div className="bg-sidebar-border my-1 h-px w-6" />

            <CollapsedTooltip label="대시보드">
              <button
                type="button"
                onClick={() => navigate('/')}
                className={`hover:bg-sidebar-accent flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                  location.pathname === '/'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="대시보드로 이동"
              >
                <LayoutDashboard className="h-4 w-4" />
              </button>
            </CollapsedTooltip>

            <CollapsedTooltip label="에이전트 상태">
              <button
                type="button"
                onClick={() => navigate('/agent-status')}
                className={`hover:bg-sidebar-accent flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                  location.pathname.startsWith('/agent-status')
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="에이전트 상태로 이동"
              >
                <Activity className="h-4 w-4" />
              </button>
            </CollapsedTooltip>

            <CollapsedTooltip label={theme === 'dark' ? '라이트 모드' : '다크 모드'}>
              <button
                type="button"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                aria-label={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
            </CollapsedTooltip>

            {currentChatSessionId !== null && (
              <CollapsedTooltip label="활동 패널">
                <button
                  type="button"
                  onClick={() => setTaskActivityPanelOpen(true)}
                  className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                  aria-label="활동 패널 열기"
                >
                  <PanelRightOpen className="h-4 w-4" />
                </button>
              </CollapsedTooltip>
            )}

            <div className="bg-sidebar-border my-1 h-px w-6" />

            {/* New Chat button */}
            <CollapsedTooltip label="새 채팅">
              <button
                type="button"
                onClick={handleNewChat}
                className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
              >
                <Plus className="h-4 w-4" />
              </button>
            </CollapsedTooltip>

            {/* Sessions icon — hover로 팝오버 */}
            <Popover open={sessionsPopoverOpen} onOpenChange={setSessionsPopoverOpen}>
              <PopoverTrigger asChild>
                <button
                  onMouseEnter={() => setSessionsPopoverOpen(true)}
                  onMouseLeave={() => setSessionsPopoverOpen(false)}
                  className="hover:bg-sidebar-accent text-muted-foreground relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                >
                  <MessageSquare className="h-4 w-4" />
                </button>
              </PopoverTrigger>
              <PopoverContent
                side="right"
                align="start"
                className="w-72 rounded-2xl p-3"
                onMouseEnter={() => setSessionsPopoverOpen(true)}
                onMouseLeave={() => setSessionsPopoverOpen(false)}
              >
                <div className="mb-2">
                  <h3 className="text-foreground mb-1 text-sm font-semibold">대화 세션</h3>
                  <p className="text-muted-foreground text-xs">최근 대화 세션</p>
                </div>
                <div className="space-y-1.5">
                  {sidebarSessions.slice(0, 3).map((session) => {
                    const isActive =
                      location.pathname === '/agent-status' && selectedSessionId === session.id
                    const isChatActive = location.pathname === `/session/${session.id}`
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate('/agent-status')
                          setSessionsPopoverOpen(false)
                        }}
                        className={`cursor-pointer rounded-lg p-2.5 transition-colors ${
                          isActive
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                            : 'hover:bg-muted'
                        }`}
                      >
                        <div className="mb-1 flex items-center justify-between gap-1">
                          <p
                            className={`truncate text-sm ${isActive ? 'text-sidebar-accent-foreground font-medium' : 'text-foreground/80'}`}
                          >
                            {session.title}
                          </p>
                          <button
                            type="button"
                            aria-label="채팅 열기"
                            onClick={(event) => {
                              handleOpenChatSession(session.id, event)
                              setSessionsPopoverOpen(false)
                            }}
                            className={`relative flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors ${
                              isChatActive
                                ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                            }`}
                          >
                            {session.isRunning && (
                              <Loader2 className="text-primary absolute -top-0.5 -right-0.5 h-3 w-3 animate-spin" />
                            )}
                            <MessageCircle className="h-4 w-4" />
                          </button>
                        </div>
                        <p className="text-muted-foreground truncate text-xs">{session.preview}</p>
                        <div className="mt-1 flex items-center gap-1">
                          <Clock className="text-muted-foreground h-3 w-3" />
                          <span className="text-muted-foreground text-xs">{session.time}</span>
                        </div>
                      </div>
                    )
                  })}
                  {sidebarSessions.length === 0 && (
                    <EmptySessionNotice
                      realtimeStatus={realtimeStatus}
                      loading={sessionListLoading}
                      error={chatError}
                    />
                  )}
                </div>
              </PopoverContent>
            </Popover>

            {/* Running session loading indicators */}
            {runningSessions.map((session) => (
              <CollapsedTooltip key={session.id} label={session.title}>
                <button
                  onClick={(event) => handleOpenChatSession(session.id, event)}
                  aria-label="채팅 열기"
                  className={`hover:bg-sidebar-accent relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
                    location.pathname === `/session/${session.id}`
                      ? 'text-primary'
                      : 'text-muted-foreground'
                  }`}
                >
                  <Loader2 className="text-primary absolute top-1 right-1 h-3 w-3 animate-spin" />
                  <MessageCircle className="h-4 w-4" strokeWidth={2.5} />
                </button>
              </CollapsedTooltip>
            ))}

            <div className="flex-1" />

            {/* Profile icon (collapsed) */}
            <div className="bg-sidebar-border my-1 h-px w-6" />
            <Popover open={profileOpen} onOpenChange={setProfileOpen}>
              <PopoverTrigger asChild>
                <CollapsedTooltip label="프로필">
                  <button className="hover:bg-sidebar-accent flex h-9 w-9 items-center justify-center rounded-lg transition-colors">
                    <ProfileAvatar size={32} />
                  </button>
                </CollapsedTooltip>
              </PopoverTrigger>
              <PopoverContent side="right" align="end" className="w-52 rounded-2xl p-1.5">
                <ProfileMenu
                  onSettingsClick={() => {
                    setProfileOpen(false)
                    setSettingsOpen(true)
                  }}
                />
              </PopoverContent>
            </Popover>
          </div>
        )}

        {/* ── Expanded Panel ── */}
        {!collapsed && (
          <div className="flex h-full flex-col overflow-hidden">
            <div className="border-sidebar-border shrink-0 border-b px-3 py-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="hover:bg-sidebar-accent flex min-w-0 items-center gap-2 rounded-lg p-1.5 transition-colors"
                  aria-label="홈으로 이동"
                >
                  <img
                    src="/logo-sidebar.png"
                    alt="HeyGent"
                    className="h-14 w-28 shrink-0 rounded-lg object-contain"
                  />
                </button>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-8 w-8 items-center justify-center rounded-md transition-colors"
                    aria-label={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
                    title={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
                  >
                    {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => setSidebarCollapsed(true)}
                    className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-8 w-8 items-center justify-center rounded-md transition-colors"
                    aria-label="사이드바 접기"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <nav className="space-y-1">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                    location.pathname === '/'
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                      : 'text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
                  }`}
                >
                  <LayoutDashboard className="h-4 w-4 shrink-0" />
                  <span>대시보드</span>
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/agent-status')}
                  className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                    location.pathname.startsWith('/agent-status')
                      ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                      : 'text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
                  }`}
                >
                  <Activity className="h-4 w-4 shrink-0" />
                  <span>에이전트 상태</span>
                </button>
              </nav>

              {currentChatSessionId !== null && (
                <CurrentChatSidebarControl
                  title={currentChatTitle}
                  connectionState={connectionState}
                  onOpenActivity={() => setTaskActivityPanelOpen(true)}
                  onOpenSettings={() => setSessionSettingsSessionId(currentChatSessionId)}
                />
              )}
            </div>

            <div className="flex-1 overflow-x-hidden overflow-y-auto px-3 py-3">
              {/* ── Sessions ── */}
              <section>
                <div className="text-muted-foreground mb-2 flex items-center gap-2 px-1 text-xs font-medium">
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>대화 세션</span>
                </div>
                <div className="space-y-1">
                  {/* New Chat button */}
                  <button
                    onClick={handleNewChat}
                    className="hover:bg-sidebar-accent border-sidebar-border flex w-full items-center gap-2 rounded-lg border border-dashed p-2.5 transition-colors"
                  >
                    <Plus className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                    <span className="text-muted-foreground text-sm">새 채팅 시작</span>
                  </button>

                  {sidebarSessions.map((session) => {
                    const isActive =
                      location.pathname === '/agent-status' && selectedSessionId === session.id
                    const isChatActive = location.pathname === `/session/${session.id}`
                    const isPinned = pinnedSessionIds.has(session.id)
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate('/agent-status')
                        }}
                        className={`group flex cursor-pointer items-center gap-2 rounded-lg p-2.5 transition-colors ${
                          isActive
                            ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                            : 'hover:bg-sidebar-accent'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="mb-0.5 flex items-center gap-1">
                            {isPinned && <Pin className="text-primary h-3 w-3 shrink-0" />}
                            <p
                              className={`truncate text-sm ${isActive ? 'text-sidebar-accent-foreground font-medium' : 'text-foreground/80'}`}
                            >
                              {session.title}
                            </p>
                          </div>
                          <p className="text-muted-foreground truncate text-xs">
                            {session.preview}
                          </p>
                          <div className="mt-1.5 flex items-center gap-1">
                            <Clock className="text-muted-foreground h-3 w-3" />
                            <span className="text-muted-foreground text-xs">{session.time}</span>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          {/* ⋯ menu */}
                          <Popover>
                            <PopoverTrigger asChild>
                              <button
                                type="button"
                                aria-label="세션 옵션"
                                onClick={(e) => e.stopPropagation()}
                                className="text-muted-foreground hover:bg-sidebar-accent hover:text-foreground flex h-7 w-7 items-center justify-center rounded-md opacity-0 transition-all group-hover:opacity-100"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </button>
                            </PopoverTrigger>
                            <PopoverContent
                              side="right"
                              align="start"
                              className="w-40 rounded-xl p-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSessionSettingsSessionId(session.id)
                                }}
                                className="hover:bg-muted flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors"
                              >
                                <Settings className="text-muted-foreground h-4 w-4 shrink-0" />
                                <span>설정</span>
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  togglePinSession(session.id)
                                }}
                                className="hover:bg-muted flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors"
                              >
                                {isPinned ? (
                                  <>
                                    <PinOff className="text-muted-foreground h-4 w-4 shrink-0" />
                                    <span>고정 해제</span>
                                  </>
                                ) : (
                                  <>
                                    <Pin className="text-muted-foreground h-4 w-4 shrink-0" />
                                    <span>채팅 고정</span>
                                  </>
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSessionConfirm({ sessionId: session.id, action: 'delete' })
                                }}
                                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-red-500 transition-colors hover:bg-red-50"
                              >
                                <Trash2 className="h-4 w-4 shrink-0" />
                                <span>삭제</span>
                              </button>
                            </PopoverContent>
                          </Popover>
                          {/* Chat open button */}
                          <button
                            type="button"
                            aria-label="채팅 열기"
                            onClick={(event) => handleOpenChatSession(session.id, event)}
                            className={`relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
                              isChatActive
                                ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                                : 'text-muted-foreground hover:bg-sidebar-accent hover:text-foreground'
                            }`}
                          >
                            {session.isRunning && (
                              <Loader2 className="text-primary absolute -top-0.5 -right-0.5 h-3 w-3 animate-spin" />
                            )}
                            <MessageCircle className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                  {sidebarSessions.length === 0 && (
                    <EmptySessionNotice
                      realtimeStatus={realtimeStatus}
                      loading={sessionListLoading}
                      error={chatError}
                    />
                  )}
                </div>
              </section>
            </div>

            {/* ── Profile Footer (Fixed) ── */}
            <div className="border-sidebar-border shrink-0 border-t px-3 py-2">
              <Popover open={profileOpen} onOpenChange={setProfileOpen}>
                <PopoverTrigger asChild>
                  <button className="hover:bg-sidebar-accent flex w-full items-center gap-3 rounded-lg p-2 transition-colors">
                    <ProfileAvatar size={32} />
                    <div className="min-w-0 flex-1 text-left">
                      <p className="text-foreground truncate text-sm font-medium">
                        <ProfileName />
                      </p>
                    </div>
                  </button>
                </PopoverTrigger>
                <PopoverContent side="top" align="start" className="w-52 rounded-2xl p-1.5">
                  <ProfileMenu
                    onSettingsClick={() => {
                      setProfileOpen(false)
                      setSettingsOpen(true)
                    }}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>
        )}

        {/* ── Resize Handle ── */}
        {!collapsed && (
          <div
            className="group absolute top-0 right-0 bottom-0 z-10 flex w-1 cursor-col-resize items-center justify-center"
            onMouseDown={startResize}
          >
            <div className="group-hover:bg-primary/30 h-8 w-0.5 rounded-full bg-transparent transition-colors" />
            <GripVertical className="text-muted-foreground/40 absolute h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
          </div>
        )}
      </div>
    </>
  )
}

function storePendingSessionConfig(config: CustomAgentConfig | undefined) {
  if (config === undefined) {
    sessionStorage.removeItem('ai-new-session-config')
    return
  }
  sessionStorage.setItem('ai-new-session-config', JSON.stringify(config))
}

function CurrentChatSidebarControl({
  title,
  connectionState,
  onOpenActivity,
  onOpenSettings,
}: {
  title: string
  connectionState: SidebarConnectionState
  onOpenActivity: () => void
  onOpenSettings: () => void
}) {
  const isBusy = connectionState === 'connecting' || connectionState === 'reconnecting'
  const isError = connectionState === 'error'

  return (
    <div className="border-sidebar-border mt-3 rounded-lg border p-2.5">
      <div className="mb-2 flex min-w-0 items-center gap-2">
        <div className="bg-muted text-muted-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-full">
          <MessageCircle className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-foreground truncate text-sm font-semibold">{title}</p>
          <div
            className={`flex items-center gap-1.5 text-xs ${
              isError ? 'text-destructive' : 'text-muted-foreground'
            }`}
          >
            {isBusy ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : isError ? (
              <AlertCircle className="h-3 w-3" />
            ) : (
              <Wifi className="h-3 w-3" />
            )}
            <span>{getSidebarConnectionText(connectionState)}</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        <button
          type="button"
          onClick={onOpenSettings}
          className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs transition-colors"
        >
          <Settings className="h-3.5 w-3.5" />
          <span>설정</span>
        </button>
        <button
          type="button"
          onClick={onOpenActivity}
          className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs transition-colors"
        >
          <PanelRightOpen className="h-3.5 w-3.5" />
          <span>활동</span>
        </button>
      </div>
    </div>
  )
}

function EmptySessionNotice({
  realtimeStatus,
  loading,
  error,
}: {
  realtimeStatus: string
  loading: boolean
  error: string | null
}) {
  const message =
    error ??
    (loading ? '세션 목록을 불러오는 중입니다.' : null) ??
    (realtimeStatus === 'authenticated' ? '아직 표시할 대화 세션이 없습니다.' : 'AI 연결 준비 중')

  return (
    <div className="border-sidebar-border text-muted-foreground rounded-lg border border-dashed p-3 text-xs leading-5">
      {message}
    </div>
  )
}

function getSessionConfirmTitle(action: SessionConfirmAction) {
  if (action === 'delete') {
    return '채팅 삭제'
  }
  return '채팅 삭제'
}

function getSessionConfirmMessage(action: SessionConfirmAction) {
  if (action === 'delete') {
    return '이 채팅을 삭제하시겠습니까? 서버의 삭제 정책에 따라 복구가 제한될 수 있습니다.'
  }
  return '이 채팅을 삭제하시겠습니까? 서버의 삭제 정책에 따라 복구가 제한될 수 있습니다.'
}

function getSessionConfirmButtonLabel(action: SessionConfirmAction) {
  if (action === 'delete') {
    return '삭제'
  }
  return '삭제'
}

function toSidebarSession(session: RawAiSession): SidebarSession {
  const title =
    getStringValue(session.title) ??
    getStringValue(session.session_key) ??
    `세션 ${session.session_id}`
  const preview =
    getStringValue(session.last_message) ??
    getStringValue(session.preview) ??
    getMessageCountPreview(session) ??
    '대화 내용 없음'
  const activeTaskRunId =
    getStringValue(session.active_task_run_id) ?? getStringValue(session.activeTaskRunId)
  const taskRunStatus =
    getStringValue(session.last_task_run_status) ?? getStringValue(session.lastTaskRunStatus)

  return {
    id: session.session_id,
    title,
    preview,
    time: formatSessionTime(session),
    isRunning:
      isRunningTaskRunStatus(taskRunStatus) ||
      (activeTaskRunId !== undefined && taskRunStatus === undefined),
    raw: session,
  }
}

function getStringValue(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value : undefined
}

function getMessageCountPreview(session: RawAiSession) {
  const count = typeof session.message_count === 'number' ? session.message_count : undefined
  if (count === undefined) {
    return undefined
  }
  return `${count}개 메시지`
}

function getSessionTime(session: RawAiSession) {
  const rawTime =
    getStringValue(session.last_message_at) ??
    getStringValue(session.updated_at) ??
    getStringValue(session.created_at)
  if (rawTime === undefined) {
    return 0
  }
  const time = new Date(rawTime).getTime()
  return Number.isFinite(time) ? time : 0
}

function formatSessionTime(session: RawAiSession) {
  const time = getSessionTime(session)
  if (time === 0) {
    return '시간 정보 없음'
  }

  return new Intl.DateTimeFormat('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(time))
}

function isRunningTaskRunStatus(status: string | undefined) {
  return status === 'PENDING' || status === 'RUNNING' || status === 'WAITING'
}

function isRemovedSidebarSession(session: RawAiSession) {
  return session.deleted_at != null || session.status === 'DELETED'
}

function getCurrentChatSessionId(pathname: string) {
  if (!pathname.startsWith('/session/')) {
    return null
  }
  const sessionId = pathname.slice('/session/'.length).split('/')[0]
  return sessionId.trim() === '' ? null : sessionId
}

function getSessionDisplayName(session: RawAiSession | null) {
  if (session === null) {
    return '새 세션'
  }
  const source = session as Record<string, unknown>
  const metadata = toPlainObject(source.metadata)
  const ui = toPlainObject(metadata.ui)
  return getTrimmedString(ui.sessionName) ?? toSidebarSession(session).title
}

function toPlainObject(value: unknown): Record<string, unknown> {
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }
  return {}
}

function getTrimmedString(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : undefined
}

function getSidebarConnectionState(
  connectionStatus: string,
  authStatus: string,
  accessToken: string | null,
  realtimeError: string | null,
): SidebarConnectionState {
  if (realtimeError !== null || authStatus === 'failed') {
    return 'error'
  }
  if (accessToken === null || accessToken.trim() === '') {
    return 'error'
  }

  switch (connectionStatus) {
    case 'authenticated':
      return 'connected'
    case 'connecting':
    case 'open':
      return 'connecting'
    case 'reconnecting':
      return 'reconnecting'
    case 'error':
    case 'closed':
      return 'error'
    case 'idle':
    default:
      return 'idle'
  }
}

function getSidebarConnectionText(state: SidebarConnectionState) {
  switch (state) {
    case 'connected':
      return '연결됨'
    case 'connecting':
      return '연결 중'
    case 'reconnecting':
      return '연결 복구 중'
    case 'error':
      return '연결 확인 필요'
    case 'idle':
    default:
      return '대기 중'
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Collapsed tooltip
// ────────────────────────────────────────────────────────────────────────────
function CollapsedTooltip({ label, children }: { label: string; children: React.ReactNode }) {
  const [visible, setVisible] = useState(false)
  return (
    <div
      className="relative"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {visible && (
        <div className="bg-foreground text-background pointer-events-none absolute top-1/2 left-full z-100 ml-2 -translate-y-1/2 rounded-md px-2 py-1 text-xs font-medium whitespace-nowrap shadow-lg">
          {label}
          <div
            className="pointer-events-none absolute top-1/2 -left-1.5 -translate-y-1/2"
            style={{
              borderWidth: '4px',
              borderStyle: 'solid',
              borderColor: 'transparent',
              borderRightColor: 'var(--foreground)',
            }}
          />
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Profile helpers
// ────────────────────────────────────────────────────────────────────────────
function ProfileAvatar({ size = 36 }: { size?: number }) {
  const userInfo = useAuthStore((s) => s.userInfo)
  if (userInfo?.profileImage) {
    return (
      <img
        src={userInfo.profileImage}
        alt="프로필"
        className="shrink-0 rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <div
      className="bg-primary/10 border-primary/20 flex shrink-0 items-center justify-center rounded-full border"
      style={{ width: size, height: size }}
    >
      <User className="text-primary h-4 w-4" />
    </div>
  )
}

function ProfileName() {
  const userInfo = useAuthStore((s) => s.userInfo)
  return <>{userInfo?.nickname ?? '사용자'}</>
}

// ────────────────────────────────────────────────────────────────────────────
// Profile Menu Component
// ────────────────────────────────────────────────────────────────────────────
function ProfileMenu({ onSettingsClick }: { onSettingsClick: () => void }) {
  const [view, setView] = useState<'menu' | 'profile'>('menu')
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { refreshToken, clearTokens, userInfo, setUserInfo } = useAuthStore()
  const [nickname, setNickname] = useState(userInfo?.nickname ?? '')

  if (view === 'profile') {
    return (
      <div className="p-2">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-foreground text-sm font-semibold">프로필</h3>
          <button
            onClick={() => setView('menu')}
            className="hover:bg-muted flex h-6 w-6 items-center justify-center rounded-md transition-colors"
          >
            <X className="text-muted-foreground h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3">
          {/* Nickname Input */}
          <div>
            <label className="text-muted-foreground mb-1.5 block text-xs font-medium">닉네임</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={nickname}
                onChange={(e) => {
                  setNickname(e.target.value)
                  setSaveError(null)
                }}
                maxLength={100}
                disabled={isSaving}
                className="border-border bg-background text-foreground focus:ring-primary/20 flex-1 rounded-lg border px-3 py-2 text-sm focus:ring-2 focus:outline-none disabled:opacity-60"
              />
              <button
                onClick={async () => {
                  const trimmed = nickname.trim()
                  if (!trimmed || isSaving) return
                  setIsSaving(true)
                  setSaveError(null)
                  try {
                    const res = await updateMyInfo({ nickname: trimmed })
                    setUserInfo(res.data)
                  } catch {
                    setSaveError('저장에 실패했습니다.')
                  } finally {
                    setIsSaving(false)
                  }
                }}
                disabled={isSaving || !nickname.trim()}
                className="bg-primary hover:bg-primary/90 rounded-lg p-2 text-white transition-colors disabled:opacity-50"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Edit3 className="h-4 w-4" />
                )}
              </button>
            </div>
            {saveError && <p className="mt-1 text-xs text-red-500">{saveError}</p>}
          </div>

          {/* Logout Button */}
          <button
            onClick={async () => {
              if (isLoggingOut) return
              setIsLoggingOut(true)
              try {
                if (refreshToken) await logout(refreshToken)
              } finally {
                clearTokens()
                navigate('/login', { replace: true })
              }
            }}
            disabled={isLoggingOut}
            className="flex w-full items-center gap-3 rounded-xl bg-red-50 px-3 py-2.5 text-red-600 transition-colors hover:bg-red-100 disabled:opacity-60"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span className="text-sm font-medium">
              {isLoggingOut ? '로그아웃 중...' : '로그아웃'}
            </span>
          </button>
        </div>
      </div>
    )
  }

  const menuItems = [
    { icon: UserCircle, label: '프로필', action: () => setView('profile') },
    { icon: Settings, label: '설정', action: onSettingsClick },
  ]

  return (
    <div className="space-y-0.5">
      {menuItems.map((item, index) => (
        <button
          key={index}
          onClick={item.action}
          className="hover:bg-muted flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors"
        >
          <item.icon className="text-muted-foreground h-4 w-4 shrink-0" />
          <span className="text-foreground text-sm">{item.label}</span>
        </button>
      ))}
    </div>
  )
}
