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
  MoreHorizontal,
  Pin,
  PinOff,
  DoorOpen,
} from 'lucide-react'
import { useState } from 'react'
import { sessions as staticSessions } from '@/data/sessions'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SettingsDialog } from '@/components/SettingsDialog'
import { NewSessionModal, type CustomAgentConfig } from '@/components/NewSessionModal'
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
  const {
    setSelectedSessionId,
    dynamicSessions,
    removeDynamicSession,
    pinnedSessionIds,
    togglePinSession,
    hiddenSessionIds,
    hideSession,
  } = useSessionStore()

  // 숨김 제외 후 고정 세션 상단 정렬
  const allSessions = [...dynamicSessions, ...staticSessions]
    .filter((s) => !hiddenSessionIds.has(s.id))
    .sort((a, b) => {
      const ap = pinnedSessionIds.has(a.id) ? 0 : 1
      const bp = pinnedSessionIds.has(b.id) ? 0 : 1
      return ap - bp
    })

  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [profileOpen, setProfileOpen] = useState(false)
  const [sessionsPopoverOpen, setSessionsPopoverOpen] = useState(false)
  const [newSessionModalOpen, setNewSessionModalOpen] = useState(false)
  const isResizing = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)
  const navigate = useNavigate()
  const location = useLocation()

  const handleNewChat = () => {
    setNewSessionModalOpen(true)
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
      <NewSessionModal
        open={newSessionModalOpen}
        onOpenChange={setNewSessionModalOpen}
        onConfirm={(config?: CustomAgentConfig) => {
          setNewSessionModalOpen(false)
          navigate('/new-chat', { state: { customAgent: config ?? null } })
        }}
      />

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
            <CollapsedTooltip label="새 세션 시작">
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
                  {allSessions.slice(0, 3).map((session) => {
                    const isActive = location.pathname === `/session/${session.id}`
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate(`/session/${session.id}`)
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
            {allSessions
              .filter((s) => runningSessionIds.has(s.id))
              .map((s) => (
                <CollapsedTooltip key={s.id} label={s.title}>
                  <button
                    onClick={() => {
                      setSelectedSessionId(s.id)
                      navigate(`/session/${s.id}`)
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
                    <span className="text-muted-foreground text-sm">새 세션 시작</span>
                  </button>

                  {allSessions.map((session) => {
                    const isActive = location.pathname === `/session/${session.id}`
                    const isRunning = runningSessionIds.has(session.id)
                    const isPinned = pinnedSessionIds.has(session.id)
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate(`/session/${session.id}`)
                        }}
                        className={`group relative cursor-pointer rounded-lg p-2.5 transition-colors ${
                          isActive
                            ? 'bg-primary/8 border-primary/15 border'
                            : 'hover:bg-sidebar-accent border border-transparent'
                        }`}
                      >
                        {/* 상단 행: 제목 + 고정 아이콘 + 점3개 버튼 */}
                        <div className="mb-0.5 flex items-center gap-1">
                          {isPinned && (
                            <Pin className="text-primary mr-0.5 h-2.5 w-2.5 shrink-0 rotate-45" />
                          )}
                          <p
                            className={`min-w-0 flex-1 truncate text-sm ${isActive ? 'text-foreground font-medium' : 'text-foreground/80'}`}
                          >
                            {session.title}
                          </p>
                          {isRunning && (
                            <Loader2
                              className="text-primary shrink-0 animate-spin opacity-70"
                              style={{ width: '11px', height: '11px' }}
                              strokeWidth={2.5}
                            />
                          )}
                          {/* 점3개 메뉴 */}
                          <Popover>
                            <PopoverTrigger asChild>
                              <button
                                onClick={(e) => e.stopPropagation()}
                                className="text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted flex h-5 w-5 shrink-0 items-center justify-center rounded opacity-0 transition-all group-hover:opacity-100"
                              >
                                <MoreHorizontal className="h-3.5 w-3.5" />
                              </button>
                            </PopoverTrigger>
                            <PopoverContent
                              side="right"
                              align="start"
                              className="w-40 rounded-xl p-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {/* 세션 고정 */}
                              <button
                                onClick={() => togglePinSession(session.id)}
                                className="hover:bg-muted flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-colors"
                              >
                                {isPinned ? (
                                  <PinOff className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                                ) : (
                                  <Pin className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                                )}
                                <span className="text-foreground text-xs font-medium">
                                  {isPinned ? '고정 해제' : '채팅 고정'}
                                </span>
                              </button>
                              {/* 구분선 */}
                              <div className="border-border my-1 border-t" />
                              {/* 나가기 */}
                              <button
                                onClick={() => setDeleteConfirm(session.id)}
                                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-red-500 transition-colors hover:bg-red-50"
                              >
                                <DoorOpen className="h-3.5 w-3.5 shrink-0" />
                                <span className="text-xs font-medium">나가기</span>
                              </button>
                            </PopoverContent>
                          </Popover>
                        </div>

                        <p className="text-muted-foreground mb-1.5 truncate text-xs">
                          {session.preview}
                        </p>
                        <div className="flex items-center gap-1">
                          <Clock className="text-muted-foreground h-3 w-3 shrink-0" />
                          <span className="text-muted-foreground text-xs">{session.time}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            </div>

            {/* ── 나가기 확인 모달 ── */}
            {deleteConfirm && (
              <div
                className="fixed inset-0 z-200 flex items-center justify-center bg-black/40"
                onClick={() => setDeleteConfirm(null)}
              >
                <div
                  className="bg-background w-72 rounded-2xl p-5 shadow-2xl"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="mb-1 flex items-center gap-2">
                    <DoorOpen className="h-4 w-4 shrink-0 text-red-500" />
                    <h3 className="text-foreground text-sm font-semibold">세션 나가기</h3>
                  </div>
                  <p className="text-muted-foreground mb-4 text-xs leading-relaxed">
                    이 세션에서 나가면 대화 내용이 삭제됩니다.
                    <br />
                    정말 나가시겠습니까?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="bg-muted text-foreground hover:bg-muted/80 flex-1 rounded-lg py-2 text-xs font-medium transition-colors"
                    >
                      취소
                    </button>
                    <button
                      onClick={() => {
                        const id = deleteConfirm
                        const isActive = location.pathname === `/session/${id}`
                        const isDynamic = dynamicSessions.some((s) => s.id === id)
                        if (isDynamic) removeDynamicSession(id)
                        else hideSession(id)
                        setDeleteConfirm(null)
                        if (isActive) navigate('/')
                      }}
                      className="flex-1 rounded-lg bg-red-500 py-2 text-xs font-medium text-white transition-colors hover:bg-red-600"
                    >
                      나가기
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ── Profile Footer (Fixed) ── */}
            <div className="border-sidebar-border flex-shrink-0 border-t px-3 py-3">
              <Popover open={profileOpen} onOpenChange={setProfileOpen}>
                <PopoverTrigger asChild>
                  <button className="hover:bg-sidebar-accent flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors">
                    <ProfileAvatar size={28} />
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
