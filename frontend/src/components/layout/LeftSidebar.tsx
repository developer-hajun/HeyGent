import { useEffect, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router'
import {
  Activity,
  Loader2,
  LayoutDashboard,
  MessageSquare,
  Moon,
  Plus,
  Sun,
  User,
  Settings,
  LogOut,
  UserCircle,
  X,
  Edit3,
  Pin,
} from 'lucide-react'
import { useState } from 'react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SettingsDialog } from '@/components/settings/SettingsDialog'
import { NewSessionModal, type CustomAgentConfig } from '@/components/session/NewSessionModal'
import { getCurrentWorkspaceSessionId } from '@/components/sessionWorkspace/sessionWorkspaceUtils'
import {
  DEFAULT_SIDEBAR_COLLAPSED_WIDTH,
  DEFAULT_SIDEBAR_WIDTH,
  useUIStore,
} from '@/store/useUIStore'
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

export function LeftSidebar() {
  const {
    sidebarCollapsed: collapsed,
    settingsOpen,
    settingsInitialTab,
    setSidebarCollapsed,
    setSessionWorkspaceCollapsed,
    setSettingsOpen,
    theme,
    setTheme,
  } = useUIStore()
  const { setSelectedSessionId, pinnedSessionIds } = useSessionStore()
  const [profileOpen, setProfileOpen] = useState(false)
  const [newSessionModalOpen, setNewSessionModalOpen] = useState(false)
  const commandClient = useAiRealtimeStore((state) => state.commandClient)
  const realtimeStatus = useAiRealtimeStore((state) => state.connectionStatus)
  const sessionsById = useChatStore((state) => state.sessionsById)
  const sessionListLoading = useChatStore((state) => state.sessionListLoading)
  const chatError = useChatStore((state) => state.sessionListError ?? state.lastError)
  const fetchSessions = useChatStore((state) => state.fetchSessions)
  const navigate = useNavigate()
  const location = useLocation()
  const currentWorkspaceSessionId = getCurrentWorkspaceSessionId(location.pathname)
  const sidebarSessions = useMemo(() => {
    const all = Object.values(sessionsById)
      .map(toSidebarSession)
      .filter((s) => !isRemovedSidebarSession(s.raw))
      .sort((first, second) => getSessionTime(second.raw) - getSessionTime(first.raw))
    const pinned = all.filter((s) => pinnedSessionIds.has(s.id))
    const unpinned = all.filter((s) => !pinnedSessionIds.has(s.id))
    return [...pinned, ...unpinned]
  }, [sessionsById, pinnedSessionIds])

  useEffect(() => {
    if (commandClient === null) {
      return
    }

    void fetchSessions().catch(() => undefined)
  }, [commandClient, fetchSessions])

  const handleNewChat = () => {
    setNewSessionModalOpen(true)
  }

  const handleOpenPrimaryRoute = (path: string) => {
    if (collapsed) {
      setSidebarCollapsed(false)
    }
    navigate(path)
  }

  const handleOpenChatSession = (sessionId: string, event?: React.MouseEvent) => {
    event?.stopPropagation()
    setSelectedSessionId(sessionId)
    if (!collapsed) {
      setSidebarCollapsed(true)
    }
    setSessionWorkspaceCollapsed(false)
    navigate(`/session/${sessionId}`)
  }

  return (
    <>
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        sessionId={getCurrentWorkspaceSessionId(location.pathname) ?? undefined}
        initialTab={settingsInitialTab as 'apiKeys'}
      />
      <NewSessionModal
        open={newSessionModalOpen}
        onOpenChange={setNewSessionModalOpen}
        onConfirm={(config) => {
          storePendingSessionConfig(config)
          setNewSessionModalOpen(false)
          if (config && !config.seedDefaultAgents) {
            setSidebarCollapsed(false)
            navigate('/agent-status')
          } else {
            setSidebarCollapsed(true)
            navigate('/new-chat')
          }
        }}
      />

      <div
        className="bg-background border-border relative flex shrink-0 flex-col overflow-hidden border-r transition-[width] duration-200 ease-in-out"
        style={{ width: collapsed ? DEFAULT_SIDEBAR_COLLAPSED_WIDTH : DEFAULT_SIDEBAR_WIDTH }}
      >
        {/* ── Collapsed Rail ── */}
        {collapsed && (
          <div className="flex h-full flex-col items-center gap-1.5 px-2 py-4">
            <div className="flex h-12 shrink-0 items-center justify-center">
              <CollapsedTooltip label="에이전트 상태">
                <button
                  type="button"
                  onClick={() => handleOpenPrimaryRoute('/agent-status')}
                  className="hover:bg-accent/50 flex h-12 w-12 items-center justify-center rounded-xl transition-colors"
                  aria-label="에이전트 상태로 이동"
                >
                  <img src="/onlylogo.png" alt="HeyGent" className="h-9 w-9 object-contain" />
                </button>
              </CollapsedTooltip>
            </div>

            <div className="bg-border my-1 h-px w-10" />

            <CollapsedTooltip label="에이전트 상태">
              <button
                type="button"
                onClick={() => handleOpenPrimaryRoute('/agent-status')}
                className={`hover:bg-accent/50 flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                  location.pathname.startsWith('/agent-status')
                    ? 'bg-accent text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="에이전트 상태로 이동"
              >
                <Activity className="h-5 w-5" />
              </button>
            </CollapsedTooltip>

            <CollapsedTooltip label="대시보드">
              <button
                type="button"
                onClick={() => handleOpenPrimaryRoute('/')}
                className={`hover:bg-accent/50 flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                  location.pathname === '/'
                    ? 'bg-accent text-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
                aria-label="대시보드로 이동"
              >
                <LayoutDashboard className="h-5 w-5" />
              </button>
            </CollapsedTooltip>

            <div className="bg-border my-1 h-px w-10" />

            {/* New Chat button */}
            <CollapsedTooltip label="새 대화">
              <button
                type="button"
                onClick={handleNewChat}
                className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-12 w-12 items-center justify-center rounded-xl transition-colors"
              >
                <Plus className="h-5 w-5" />
              </button>
            </CollapsedTooltip>

            {sidebarSessions.map((session) => (
              <CollapsedTooltip key={session.id} label={session.title}>
                <button
                  type="button"
                  onClick={(event) => handleOpenChatSession(session.id, event)}
                  aria-label={`${session.title} 채팅 열기`}
                  className={`hover:bg-accent/50 relative flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
                    currentWorkspaceSessionId === session.id
                      ? 'bg-accent text-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {session.isRunning && (
                    <Loader2 className="text-primary absolute top-1 right-1 h-3 w-3 animate-spin" />
                  )}
                  <MessageSquare className="h-5 w-5" />
                </button>
              </CollapsedTooltip>
            ))}

            <div className="flex-1" />

            {/* Theme toggle (collapsed) */}
            <CollapsedTooltip label={theme === 'dark' ? '라이트 모드' : '다크 모드'}>
              <button
                type="button"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-12 w-12 items-center justify-center rounded-xl transition-colors"
                aria-label={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
              >
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
            </CollapsedTooltip>

            {/* Profile icon (collapsed) */}
            <div className="bg-border my-1 h-px w-10" />
            <Popover open={profileOpen} onOpenChange={setProfileOpen}>
              <CollapsedTooltip label="프로필">
                <PopoverTrigger asChild>
                  <button className="hover:bg-accent/50 flex h-12 w-12 items-center justify-center rounded-xl transition-colors">
                    <ProfileAvatar size={34} />
                  </button>
                </PopoverTrigger>
              </CollapsedTooltip>
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
            <div className="flex h-12 shrink-0 items-center gap-1 px-4">
              <button
                type="button"
                onClick={() => handleOpenPrimaryRoute('/agent-status')}
                className="hover:bg-accent/50 flex min-w-0 flex-1 items-center justify-center rounded-lg px-2 py-2 transition-colors"
                aria-label="에이전트 상태로 이동"
              >
                <img
                  src="/logo-no-character.png"
                  alt="HeyGent"
                  className="h-8 max-w-[150px] shrink-0 object-contain"
                />
              </button>
              <button
                type="button"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors"
                aria-label={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
              >
                {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </button>
            </div>

            <div className="flex-1 overflow-x-hidden overflow-y-auto px-4 py-3">
              <nav className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={() => handleOpenPrimaryRoute('/agent-status')}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    location.pathname.startsWith('/agent-status')
                      ? 'bg-accent text-foreground'
                      : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                  }`}
                >
                  <Activity className="h-5 w-5 shrink-0" />
                  <span>에이전트 상태</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleOpenPrimaryRoute('/')}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    location.pathname === '/'
                      ? 'bg-accent text-foreground'
                      : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                  }`}
                >
                  <LayoutDashboard className="h-5 w-5 shrink-0" />
                  <span>대시보드</span>
                </button>
              </nav>

              {/* ── Sessions ── */}
              <section className="mt-4">
                <div className="text-muted-foreground/60 px-3 py-1.5 font-mono text-[10px] font-medium tracking-widest">
                  <span>대화 세션</span>
                </div>
                <div className="mt-0.5 flex flex-col gap-0.5">
                  <button
                    onClick={handleNewChat}
                    className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors"
                  >
                    <Plus className="text-muted-foreground h-5 w-5 shrink-0" />
                    <span className="text-muted-foreground truncate text-sm">새 대화</span>
                  </button>

                  {sidebarSessions.map((session) => {
                    const isActive = currentWorkspaceSessionId === session.id
                    const isPinned = pinnedSessionIds.has(session.id)
                    return (
                      <button
                        type="button"
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          setSidebarCollapsed(true)
                          setSessionWorkspaceCollapsed(false)
                          navigate(`/session/${session.id}`)
                        }}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-accent text-foreground'
                            : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1">
                            {isPinned && <Pin className="text-primary h-3 w-3 shrink-0" />}
                            <p className="truncate">{session.title}</p>
                          </div>
                        </div>
                        {session.isRunning && (
                          <Loader2 className="text-primary h-3.5 w-3.5 shrink-0 animate-spin" />
                        )}
                      </button>
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
            <div className="border-border shrink-0 border-t px-4 py-3">
              <Popover open={profileOpen} onOpenChange={setProfileOpen}>
                <PopoverTrigger asChild>
                  <button className="hover:bg-accent/50 flex w-full items-center gap-3 rounded-lg p-2 transition-colors">
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
    (realtimeStatus === 'authenticated' ? '아직 표시할 대화 세션이 없습니다.' : '서버 연결 준비 중')

  return (
    <div className="border-border text-muted-foreground border border-dashed p-3 text-xs leading-5">
      {message}
    </div>
  )
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
