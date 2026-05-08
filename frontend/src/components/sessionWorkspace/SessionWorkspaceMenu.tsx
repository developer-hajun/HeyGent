import { useState } from 'react'
import {
  AlertTriangle,
  Bot,
  Check,
  ChevronLeft,
  ChevronRight,
  Edit3,
  FolderKanban,
  Loader2,
  Map,
  MessageSquare,
  Plus,
  Target,
  Trash2,
  Wifi,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { SubAgentProfileImage } from '@/components/sessionWorkspace/subAgents'
import { useChatStore } from '@/store/useChatStore'
import { useSessionStore } from '@/store/useSessionStore'
import { DEFAULT_SIDEBAR_COLLAPSED_WIDTH, DEFAULT_SIDEBAR_WIDTH } from '@/store/useUIStore'
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
  onDeleteSession: () => Promise<void>
  onOpenSubAgent: (agentPanelId: string) => void
  onSelectPanel: (panelId: WorkspaceNavId) => void
}

const MENU_ITEMS: Array<{
  id: Exclude<WorkspaceNavId, 'purpose' | 'subAgents'>
  label: string
  icon: typeof Target
}> = [
  { id: 'chat', label: '채팅', icon: MessageSquare },
  { id: 'visualization', label: '시각화', icon: Map },
  { id: 'issueBoard', label: '이슈보드', icon: FolderKanban },
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
  onDeleteSession,
  onOpenSubAgent,
  onSelectPanel,
}: SessionWorkspaceMenuProps) {
  const updateSession = useChatStore((state) => state.updateSession)
  const { agentPanelsBySessionId } = useSessionStore()
  const agentPanels = agentPanelsBySessionId[sessionId] ?? []
  const title = getSessionTitle(session)
  const mainAgentName = getMainAgentName(session)
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState(title)
  const [titleSaving, setTitleSaving] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  const handleDeleteSession = async () => {
    setDeleting(true)
    setDeleteError(null)
    try {
      await onDeleteSession()
      setDeleteDialogOpen(false)
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : '대화를 삭제하지 못했습니다.')
    } finally {
      setDeleting(false)
    }
  }

  if (collapsed) {
    return (
      <aside
        className="bg-background border-border relative flex h-full shrink-0 flex-col items-center gap-1.5 overflow-hidden border-r px-2 py-4 transition-[width] duration-200 ease-in-out"
        style={{ width: DEFAULT_SIDEBAR_COLLAPSED_WIDTH }}
      >
        <div className="flex h-12 items-center justify-center">
          <button
            type="button"
            onClick={() => onCollapsedChange(false)}
            className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-12 w-12 items-center justify-center rounded-xl transition-colors"
            aria-label="세션 메뉴 펼치기"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-auto flex h-12 items-center justify-center">
          <button
            type="button"
            onClick={() => setDeleteDialogOpen(true)}
            className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive flex h-12 w-12 items-center justify-center rounded-xl transition-colors"
            aria-label="대화 삭제"
          >
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
        <DeleteSessionDialog
          deleteError={deleteError}
          deleting={deleting}
          open={deleteDialogOpen}
          sessionTitle={title}
          onConfirm={() => void handleDeleteSession()}
          onOpenChange={(open) => {
            if (!open && !deleting) setDeleteError(null)
            setDeleteDialogOpen(open)
          }}
        />
      </aside>
    )
  }

  return (
    <aside
      className="bg-background border-border flex h-full shrink-0 flex-col border-r"
      style={{ width: DEFAULT_SIDEBAR_WIDTH }}
    >
      <div className="flex h-14 shrink-0 items-center gap-1 px-5 pt-2">
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
              className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-colors"
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
          className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors"
          aria-label="세션 메뉴 접기"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-3">
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
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
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
          <SectionHeader label="CEO" />
          <div className="group/main relative flex items-center">
            <button
              type="button"
              onClick={() => onSelectPanel('purpose')}
              className={`flex min-w-0 flex-1 items-center gap-3 rounded-lg px-3 py-2.5 pr-8 text-left text-sm font-medium transition-colors ${
                activePanel === 'purpose'
                  ? 'bg-accent text-foreground'
                  : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
              }`}
            >
              <Bot className="text-muted-foreground h-5 w-5 shrink-0" />
              <span className="truncate">{mainAgentName}</span>
            </button>
            <button
              type="button"
              onClick={() => onSelectPanel('purpose')}
              className="text-muted-foreground hover:bg-accent/50 hover:text-foreground absolute top-1/2 right-1 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-lg opacity-0 transition-opacity group-focus-within/main:opacity-100 group-hover/main:opacity-100 data-[state=open]:opacity-100"
              aria-label={`${mainAgentName} 메인 에이전트 편집`}
            >
              <Edit3 className="h-4 w-4" />
            </button>
          </div>
        </section>

        <section>
          <div className="group flex items-center">
            <button
              type="button"
              onClick={() => onSelectPanel('subAgents')}
              className="flex min-w-0 flex-1 items-center gap-1 rounded-lg px-3 py-1.5 text-left"
            >
              <ChevronRight className="text-muted-foreground/60 h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
              <span className="text-muted-foreground/60 font-mono text-[10px] font-medium tracking-widest uppercase">
                에이전트
              </span>
            </button>
            <button
              type="button"
              onClick={onCreateSubAgent}
              className="text-muted-foreground/60 hover:bg-accent/50 hover:text-foreground mr-1 flex h-7 w-7 items-center justify-center rounded-lg transition-colors"
              aria-label="에이전트 추가"
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
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onOpenSubAgent(item.id)}
                    className={`flex min-w-0 items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                      activePanel === 'subAgents' && activeSubAgentId === item.id
                        ? 'bg-accent text-foreground'
                        : 'text-foreground/80 hover:bg-accent/50 hover:text-foreground'
                    }`}
                  >
                    <SubAgentProfileImage
                      accent={item.agent.accent}
                      profileImage={item.agent.profileImage}
                      spriteId={item.agent.spriteId}
                    />
                    <span className="truncate">{item.agent.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      </nav>
      <div className="border-border/70 shrink-0 border-t px-4 py-3">
        <button
          type="button"
          onClick={() => setDeleteDialogOpen(true)}
          className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors"
        >
          <Trash2 className="h-4 w-4 shrink-0" />
          <span className="truncate">대화 삭제</span>
        </button>
      </div>
      <DeleteSessionDialog
        deleteError={deleteError}
        deleting={deleting}
        open={deleteDialogOpen}
        sessionTitle={title}
        onConfirm={() => void handleDeleteSession()}
        onOpenChange={(open) => {
          if (!open && !deleting) setDeleteError(null)
          setDeleteDialogOpen(open)
        }}
      />
    </aside>
  )
}

function DeleteSessionDialog({
  deleteError,
  deleting,
  open,
  sessionTitle,
  onConfirm,
  onOpenChange,
}: {
  deleteError: string | null
  deleting: boolean
  open: boolean
  sessionTitle: string
  onConfirm: () => void
  onOpenChange: (open: boolean) => void
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>정말로 삭제하시겠습니까?</AlertDialogTitle>
          <AlertDialogDescription>
            `{sessionTitle}` 대화와 저장된 메시지가 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {deleteError ? <p className="text-destructive text-sm">{deleteError}</p> : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>취소</AlertDialogCancel>
          <Button variant="destructive" onClick={onConfirm} disabled={deleting}>
            {deleting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                삭제 중
              </>
            ) : (
              '삭제'
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
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

function getMainAgentName(session: RawAiSession | null) {
  if (session === null) {
    return '메인 에이전트'
  }
  const metadata = toJsonObject(session.metadata)
  const uiMetadata = toJsonObject(metadata.ui)
  return getString(uiMetadata, 'agentName') ?? '메인 에이전트'
}

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-1.5">
      <span className="text-muted-foreground/60 font-mono text-[10px] font-medium tracking-widest uppercase">
        {label}
      </span>
    </div>
  )
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
