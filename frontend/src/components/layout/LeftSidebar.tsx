import { useRef, useCallback, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router'
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  MessageSquare,
  Clock,
  ListTodo,
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
import { motion } from 'motion/react'
import { sessions } from '@/data/sessions'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SettingsDialog } from '@/components/SettingsDialog'
import { useUIStore } from '@/store/useUIStore'
import { useSessionStore } from '@/store/useSessionStore'

interface Task {
  id: string
  title: string
  status: 'running' | 'completed'
  time: string
  agent: string
}

const ongoingTasks: Task[] = [
  { id: 'T-1', title: 'PR #245 보안 분석', agent: '코드 리뷰', status: 'running', time: '2분 전' },
  {
    id: 'T-2',
    title: '식사 추천 생성 중',
    agent: '식단 & 웰니스',
    status: 'running',
    time: '1분 전',
  },
  { id: 'T-3', title: '일일 알림 설정', agent: '스케줄러', status: 'running', time: '5분 전' },
]

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
  const [tasksPopoverOpen, setTasksPopoverOpen] = useState(false)
  const [sessionsPopoverOpen, setSessionsPopoverOpen] = useState(false)
  const isResizing = useRef(false)
  const startX = useRef(0)
  const startWidth = useRef(0)
  const navigate = useNavigate()
  const location = useLocation()

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
        className="bg-sidebar border-sidebar-border relative flex flex-shrink-0 flex-col border-r transition-[width] duration-200 ease-in-out"
        style={{ width: collapsed ? 52 : width }}
      >
        {/* ── Collapsed Rail ── */}
        {collapsed && (
          <div className="flex h-full flex-col items-center gap-1 py-3">
            {/* Expand button */}
            <button
              onClick={() => setSidebarCollapsed(false)}
              title="Expand sidebar"
              className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>

            <div className="bg-sidebar-border my-1 h-px w-6" />

            {/* Ongoing tasks icon */}
            <Popover open={tasksPopoverOpen} onOpenChange={setTasksPopoverOpen}>
              <PopoverTrigger asChild>
                <div className="group relative">
                  <button
                    title="실행 중인 작업"
                    className="hover:bg-sidebar-accent text-primary flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                  >
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </button>
                  <span
                    className="bg-primary absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full text-white"
                    style={{ fontSize: '9px' }}
                  >
                    {ongoingTasks.length}
                  </span>
                </div>
              </PopoverTrigger>
              <PopoverContent side="right" align="start" className="w-72 rounded-2xl p-3">
                <div className="mb-2">
                  <h3 className="text-foreground mb-1 text-sm font-semibold">실행 중인 작업</h3>
                  <p className="text-muted-foreground text-xs">
                    현재 진행 중인 {ongoingTasks.length}개의 작업
                  </p>
                </div>
                <div className="space-y-2">
                  {ongoingTasks.map((task) => (
                    <div
                      key={task.id}
                      className="bg-primary/5 border-primary/15 hover:bg-primary/8 cursor-pointer rounded-lg border p-3 transition-colors"
                    >
                      <p className="text-foreground mb-1 text-sm font-medium">{task.title}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-primary text-xs font-medium">{task.agent}</span>
                        <span className="text-muted-foreground text-xs">{task.time}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </PopoverContent>
            </Popover>

            <div className="bg-sidebar-border my-1 h-px w-6" />

            {/* Sessions icon */}
            <Popover open={sessionsPopoverOpen} onOpenChange={setSessionsPopoverOpen}>
              <PopoverTrigger asChild>
                <button
                  title="대화 세션"
                  className="hover:bg-sidebar-accent text-muted-foreground flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
                >
                  <MessageSquare className="h-4 w-4" />
                </button>
              </PopoverTrigger>
              <PopoverContent side="right" align="start" className="w-72 rounded-2xl p-3">
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
                        <p
                          className={`mb-1 truncate text-sm ${isActive ? 'text-foreground font-medium' : 'text-foreground/80'}`}
                        >
                          {session.title}
                        </p>
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

            <div className="flex-1" />

            {/* Profile icon (collapsed) */}
            <div className="bg-sidebar-border my-1 h-px w-6" />
            <Popover open={profileOpen} onOpenChange={setProfileOpen}>
              <PopoverTrigger asChild>
                <button
                  title="프로필"
                  className="hover:bg-sidebar-accent bg-primary/10 border-primary/20 flex h-9 w-9 items-center justify-center rounded-lg border transition-colors"
                >
                  <User className="text-primary h-4 w-4" />
                </button>
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
                <ListTodo className="text-muted-foreground h-4 w-4" />
                <span className="text-foreground text-sm font-semibold">활동</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  title="새 채팅"
                  className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className="hover:bg-sidebar-accent text-muted-foreground hover:text-foreground flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <div className="flex-1 space-y-6 overflow-x-hidden overflow-y-auto px-3 py-3">
              {/* ── Ongoing Tasks ── */}
              <section>
                <div className="mb-3 flex items-center gap-2 px-2">
                  <div className="bg-primary/10 flex h-7 w-7 items-center justify-center rounded-lg">
                    <Loader2 className="text-primary h-3.5 w-3.5 animate-spin" />
                  </div>
                  <span className="text-foreground text-xs font-semibold">실행 중인 작업</span>
                  <span className="bg-primary/10 text-primary ml-auto rounded-full px-2 py-0.5 text-xs font-medium">
                    {ongoingTasks.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {ongoingTasks.map((task) => (
                    <motion.div
                      key={task.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="bg-primary/5 border-primary/15 hover:bg-primary/8 group cursor-pointer rounded-xl border p-3 transition-colors"
                    >
                      <p className="text-foreground mb-1 truncate text-sm font-medium">
                        {task.title}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-primary text-xs font-medium">{task.agent}</span>
                        <span className="text-muted-foreground text-xs">{task.time}</span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </section>

              {/* Divider */}
              <div className="bg-sidebar-border h-px" />

              {/* ── Sessions ── */}
              <section>
                <div className="mb-3 flex items-center gap-2 px-2">
                  <div className="bg-muted flex h-7 w-7 items-center justify-center rounded-lg">
                    <MessageSquare className="text-muted-foreground h-3.5 w-3.5" />
                  </div>
                  <span className="text-foreground text-xs font-semibold">대화 세션</span>
                </div>
                <div className="space-y-1">
                  {sessions.map((session) => {
                    const isActive =
                      location.pathname === '/agent-status' && selectedSessionId === session.id
                    return (
                      <div
                        key={session.id}
                        onClick={() => {
                          setSelectedSessionId(session.id)
                          navigate('/agent-status')
                        }}
                        className={`cursor-pointer rounded-lg p-2.5 transition-colors ${
                          isActive
                            ? 'bg-primary/8 border-primary/15 border'
                            : 'hover:bg-sidebar-accent border border-transparent'
                        }`}
                      >
                        <p
                          className={`mb-1 truncate text-sm ${isActive ? 'text-foreground font-medium' : 'text-foreground/80'}`}
                        >
                          {session.title}
                        </p>
                        <p className="text-muted-foreground truncate text-xs">{session.preview}</p>
                        <div className="mt-1.5 flex items-center gap-1">
                          <Clock className="text-muted-foreground h-3 w-3" />
                          <span className="text-muted-foreground text-xs">{session.time}</span>
                        </div>
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
                    <div className="bg-primary/10 border-primary/20 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border">
                      <User className="text-primary h-4.5 w-4.5" />
                    </div>
                    <div className="min-w-0 flex-1 text-left">
                      <p className="text-foreground truncate text-sm font-medium">김민수</p>
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
// Profile Menu Component
// ────────────────────────────────────────────────────────────────────────────
function ProfileMenu({ onSettingsClick }: { onSettingsClick: () => void }) {
  const [view, setView] = useState<'menu' | 'profile'>('menu')
  const [nickname, setNickname] = useState('김민수')

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
                onChange={(e) => setNickname(e.target.value)}
                className="border-border text-foreground focus:ring-primary/20 flex-1 rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
              />
              <button className="bg-primary hover:bg-primary/90 rounded-lg p-2 text-white transition-colors">
                <Edit3 className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Logout Button */}
          <button className="flex w-full items-center gap-3 rounded-xl bg-red-50 px-3 py-2.5 text-red-600 transition-colors hover:bg-red-100">
            <LogOut className="h-4 w-4 flex-shrink-0" />
            <span className="text-sm font-medium">로그아웃</span>
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
