import { useState } from 'react'
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Edit3,
  Loader2,
  Map,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Plus,
  SlidersHorizontal,
  Target,
  Trash2,
  Wifi,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useChatStore } from '@/store/useChatStore'
import { useSessionStore } from '@/store/useSessionStore'
import { DEFAULT_SIDEBAR_WIDTH } from '@/store/useUIStore'
import type { RawAiSession } from '@/types/aiChat'
import { getString, getWorkspaceConnectionText, toJsonObject } from './sessionWorkspaceUtils'
import type { WorkspaceConnectionState } from './sessionWorkspaceUtils'
import type { WorkspaceNavId, WorkspacePanelId } from './sessionWorkspaceTypes'

interface SessionWorkspaceMenuProps {
  activePanel: WorkspacePanelId | null
  collapsed: boolean
  connectionState: WorkspaceConnectionState
  currentRoute: 'chat' | 'visualization'
  session: RawAiSession | null
  sessionId: string
  activeSubAgentId: string | null
  onCollapsedChange: (collapsed: boolean) => void
  onCreateSubAgent: () => void
  onEditSubAgent: (agentPanelId: string) => void
  onSelectPanel: (panelId: WorkspaceNavId) => void
}

const MENU_ITEMS: Array<{
  id: Exclude<WorkspaceNavId, 'subAgents'>
  label: string
  icon: typeof Target
}> = [
  { id: 'chat', label: '채팅', icon: MessageSquare },
  { id: 'purpose', label: '목표', icon: Target },
  { id: 'settings', label: '설정', icon: SlidersHorizontal },
  { id: 'visualization', label: '시각화', icon: Map },
]

export function SessionWorkspaceMenu({
  activePanel,
  collapsed,
  connectionState,
  currentRoute,
  session,
  sessionId,
  activeSubAgentId,
  onCollapsedChange,
  onCreateSubAgent,
  onEditSubAgent,
  onSelectPanel,
}: SessionWorkspaceMenuProps) {
  const updateSession = useChatStore((state) => state.updateSession)
  const { agentPanelsBySessionId, removeAgentPanelFromSession } = useSessionStore()
  const agentPanels = agentPanelsBySessionId[sessionId] ?? []
  const title = getSessionTitle(session)
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState(title)
  const [titleSaving, setTitleSaving] = useState(false)

  const handleSaveTitle = async () => {
    const trimmed = titleDraft.trim()
    if (session === null || trimmed === '' || trimmed === title) {
      setTitleDraft(title)
      setEditingTitle(false)
      return
    }

    const metadata = toJsonObject(session.metadata)
    const uiMetadata = toJsonObject(metadata.ui)
    setTitleSaving(true)
    try {
      await updateSession({
        sessionId: session.session_id,
        metadataPatch: { ui: { ...uiMetadata, sessionName: trimmed } },
      })
      setEditingTitle(false)
    } finally {
      setTitleSaving(false)
    }
  }

  if (collapsed) {
    return (
      <aside className="bg-background border-border flex h-full w-12 shrink-0 flex-col items-center border-r">
        <div className="flex h-12 items-center justify-center">
          <button
            type="button"
            onClick={() => onCollapsedChange(false)}
            className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 items-center justify-center transition-colors"
            aria-label="세션 메뉴 펼치기"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </aside>
    )
  }

  return (
    <aside
      className="bg-background border-border flex h-full shrink-0 flex-col border-r"
      style={{ width: DEFAULT_SIDEBAR_WIDTH }}
    >
      <div className="flex h-12 shrink-0 items-center gap-1 px-3">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          {editingTitle ? (
            <input
              autoFocus
              value={titleDraft}
              onChange={(event) => setTitleDraft(event.target.value)}
              onBlur={() => void handleSaveTitle()}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.currentTarget.blur()
                }
                if (event.key === 'Escape') {
                  setTitleDraft(title)
                  setEditingTitle(false)
                }
              }}
              className="border-border bg-background text-foreground focus:ring-ring h-8 min-w-0 flex-1 border px-2 text-sm font-medium outline-none focus:ring-1"
            />
          ) : (
            <h2 className="text-foreground truncate text-sm font-semibold">{title}</h2>
          )}
          {session !== null && (
            <button
              type="button"
              onClick={() => {
                setTitleDraft(title)
                setEditingTitle(true)
              }}
              className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-7 w-7 shrink-0 items-center justify-center transition-colors"
              aria-label="세션 이름 편집"
            >
              {titleSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : editingTitle ? (
                <Check className="h-4 w-4" />
              ) : (
                <Edit3 className="h-4 w-4" />
              )}
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => onCollapsedChange(true)}
          className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center transition-colors"
          aria-label="세션 메뉴 접기"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-3 py-2">
        <div>
          <ConnectionStatusRow state={connectionState} />
          <div className="mt-0.5 flex flex-col gap-0.5">
            {MENU_ITEMS.map((item) => {
              const Icon = item.icon
              const isActive =
                activePanel === null ? currentRoute === item.id : activePanel === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectPanel(item.id)}
                  className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent text-foreground'
                      : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                  }`}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <span className="block truncate">{item.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        <section>
          <div className="group flex items-center px-3 py-1.5">
            <button
              type="button"
              onClick={() => onSelectPanel('subAgents')}
              className="flex min-w-0 flex-1 items-center gap-1 text-left"
            >
              <ChevronRight className="text-muted-foreground/60 h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
              <span className="text-muted-foreground/60 font-mono text-[10px] font-medium tracking-widest uppercase">
                서브에이전트
              </span>
            </button>
            <button
              type="button"
              onClick={onCreateSubAgent}
              className="text-muted-foreground/60 hover:bg-accent/50 hover:text-foreground flex h-7 w-7 items-center justify-center transition-colors"
              aria-label="서브에이전트 추가"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-0.5">
            {agentPanels.length === 0 ? (
              <p className="text-muted-foreground px-3 py-2.5 text-sm font-medium">
                추가된 에이전트 없음
              </p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {agentPanels.map((item) => (
                  <div key={item.id} className="group/agent relative flex items-center">
                    <button
                      type="button"
                      onClick={() => onEditSubAgent(item.id)}
                      className={`flex min-w-0 flex-1 items-center gap-3 px-3 py-2.5 pr-8 text-left text-sm font-medium transition-colors ${
                        activePanel === 'subAgents' && activeSubAgentId === item.id
                          ? 'bg-accent text-foreground'
                          : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                      }`}
                    >
                      <item.agent.icon
                        className="text-muted-foreground h-5 w-5 shrink-0"
                        style={{ color: item.agent.accent }}
                      />
                      <span className="truncate">{item.agent.name}</span>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          type="button"
                          className="text-muted-foreground hover:bg-accent/50 hover:text-foreground pointer-events-none absolute top-1/2 right-1 flex h-7 w-7 -translate-y-1/2 items-center justify-center opacity-0 transition-opacity group-focus-within/agent:pointer-events-auto group-focus-within/agent:opacity-100 group-hover/agent:pointer-events-auto group-hover/agent:opacity-100 data-[state=open]:pointer-events-auto data-[state=open]:opacity-100"
                          aria-label={`${item.agent.name} 액션`}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-36">
                        <DropdownMenuItem onClick={() => onEditSubAgent(item.id)}>
                          <Pencil className="size-4" />
                          <span>편집</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => {
                            removeAgentPanelFromSession(sessionId, item.id)
                          }}
                        >
                          <Trash2 className="size-4" />
                          <span>삭제</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </nav>
    </aside>
  )
}

function getSessionTitle(session: RawAiSession | null) {
  if (session === null) {
    return '세션'
  }
  const metadata = toJsonObject(session.metadata)
  const uiMetadata = toJsonObject(metadata.ui)
  return getString(uiMetadata, 'sessionName') ?? getTrimmedString(session.title) ?? '세션'
}

function ConnectionStatusRow({ state }: { state: WorkspaceConnectionState }) {
  const isError = state === 'error'
  const isConnected = state === 'connected'
  const Icon = isError ? AlertTriangle : Wifi
  const label = isError
    ? '서버 연결 확인 필요'
    : isConnected
      ? '서버 연결됨'
      : getWorkspaceConnectionText(state)

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium ${
        isError
          ? 'text-destructive'
          : isConnected
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-muted-foreground'
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </div>
  )
}

function getTrimmedString(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : undefined
}
