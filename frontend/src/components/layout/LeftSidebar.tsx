import { useRef, useCallback, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router'
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  MessageSquare,
  Clock,
  GripVertical,
  Plus,
  User,
  Settings,
  LogOut,
  UserCircle,
  X,
  Edit3,
} from 'lucide-react'
import { useState } from 'react'
import { sessions } from '@/data/sessions'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SettingsDialog } from '@/components/SettingsDialog'
import { useUIStore } from '@/store/useUIStore'
import { useSessionStore } from '@/store/useSessionStore'
import { useAuthStore } from '@/store/useAuthStore'
import { logout } from '@/apis/auth'
import { updateMyInfo } from '@/apis/users'

const runningSessionIds = new Set(['S-1', 'S-3'])

export function LeftSidebar() {
  const {
    sidebarCollapsed: collapsed,
    sidebarWidth: width,
    settingsOpen,
    setSidebarCollapsed,
    clampSidebarWidth,
    setSettingsOpen,
  } = useUIStore()
  const { selectedSessionId, setSelectedSessionId } = useSessionStore()
  const [profileOpen, setProfileOpen] = useState(false)
  const [sessionsPopoverOpen, setSessionsPopoverOpen] = useState(false)
  const isResizing = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)
  const navigate = useNavigate()
  const location = useLocation()

  const handleNewChat = () => {
    navigate('/new-chat')
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
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      <div
        className="bg-sidebar border-sidebar-border relative flex flex-shrink-0 flex-col overflow-hidden border-r transition-[width] duration-200 ease-in-out"
        style={{ width: collapsed ? 52 : width }}
      >
        {/* ── Collapsed Rail ── */}
        {collapsed && (
          <div className="flex h-full flex-col items-center gap-1 py-3">
            {/* Expand button */}
            <CollapsedTooltip label="사이드바 열기">
              <button
                onClick={() => setSidebarCollapsed(false)}
                className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </CollapsedTooltip>

            <div className="bg-sidebar-border my-1 h-px w-6" />

            {/* New Chat button */}
            <CollapsedTooltip label="새 채팅">
              <button
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
                  {sessions.slice(0, 3).map((session) => {
                    const isActive =
                      location.pathname === '/agent-status' && selectedSessionId === session.id
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
                            ? 'bg-primary/8 border-primary/15 border'
                            : 'hover:bg-muted border border-transparent'
                        }`}
                      >
                        <div className="mb-1 flex items-center justify-between gap-1">
                          <p
                            className={`truncate text-sm ${isActive ? 'text-foreground font-medium' : 'text-foreground/80'}`}
                          >
                            {session.title}
                          </p>
                          {runningSessionIds.has(session.id) && (
                            <Loader2
                              className="text-primary shrink-0 animate-spin"
                              style={{ width: '16px', height: '16px' }}
                              strokeWidth={2.5}
                            />
                          )}
                        </div>
                        <p className="text-muted-foreground truncate text-xs">{session.preview}</p>
                        <div className="mt-1 flex items-center gap-1">
                          <Clock className="text-muted-foreground h-3 w-3" />
                          <span className="text-muted-foreground text-xs">{session.time}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </PopoverContent>
            </Popover>

            {/* Running session loading indicators */}
            {sessions
              .filter((s) => runningSessionIds.has(s.id))
              .map((s) => (
                <CollapsedTooltip key={s.id} label={s.title}>
                  <button
                    onClick={() => {
                      setSelectedSessionId(s.id)
                      navigate('/agent-status')
                    }}
                    className="hover:bg-sidebar-accent text-primary flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                  >
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2.5} />
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
            {/* Header */}
            <div className="border-sidebar-border flex h-12 flex-shrink-0 items-center justify-between border-b px-4">
              <div className="flex items-center gap-2">
                <MessageSquare className="text-muted-foreground h-4 w-4" />
                <span className="text-foreground text-sm font-semibold">대화 세션</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-x-hidden overflow-y-auto px-3 py-3">
              {/* ── Sessions ── */}
              <section>
                <div className="space-y-1">
                  {/* New Chat button */}
                  <button
                    onClick={handleNewChat}
                    className="hover:bg-sidebar-accent border-sidebar-border flex w-full items-center gap-2 rounded-lg border border-dashed p-2.5 transition-colors"
                  >
                    <Plus className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                    <span className="text-muted-foreground text-sm">새 채팅 시작</span>
                  </button>

                  {sessions.map((session) => {
                    const isActive =
                      location.pathname === '/agent-status' && selectedSessionId === session.id
                    const isRunning = runningSessionIds.has(session.id)
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate('/agent-status')
                        }}
                        className={`flex cursor-pointer items-center gap-2 rounded-lg p-2.5 transition-colors ${
                          isActive
                            ? 'bg-primary/8 border-primary/15 border'
                            : 'hover:bg-sidebar-accent border border-transparent'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <p
                            className={`mb-0.5 truncate text-sm ${isActive ? 'text-foreground font-medium' : 'text-foreground/80'}`}
                          >
                            {session.title}
                          </p>
                          <p className="text-muted-foreground truncate text-xs">
                            {session.preview}
                          </p>
                          <div className="mt-1.5 flex items-center gap-1">
                            <Clock className="text-muted-foreground h-3 w-3" />
                            <span className="text-muted-foreground text-xs">{session.time}</span>
                          </div>
                        </div>
                        {isRunning && (
                          <Loader2
                            className="text-primary shrink-0 animate-spin"
                            style={{ width: '18px', height: '18px' }}
                            strokeWidth={2.5}
                          />
                        )}
                      </div>
                    )
                  })}
                </div>
              </section>
            </div>

            {/* ── Profile Footer (Fixed) ── */}
            <div className="border-sidebar-border flex-shrink-0 border-t p-3">
              <Popover open={profileOpen} onOpenChange={setProfileOpen}>
                <PopoverTrigger asChild>
                  <button className="hover:bg-sidebar-accent flex w-full items-center gap-3 rounded-lg p-2.5 transition-colors">
                    <ProfileAvatar size={36} />
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
                className="border-border text-foreground focus:ring-primary/20 flex-1 rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none disabled:opacity-60"
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
            <LogOut className="h-4 w-4 flex-shrink-0" />
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
          <item.icon className="text-muted-foreground h-4 w-4 flex-shrink-0" />
          <span className="text-foreground text-sm">{item.label}</span>
        </button>
      ))}
    </div>
  )
}
