import { MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { AgentPanelItem } from '@/store/useSessionStore'
import { SubAgentProfileImage } from './SubAgentProfileImage'

export function SubAgentList({
  agentPanels,
  onCreate,
  onEdit,
  onOpen,
  onRemove,
}: {
  agentPanels: AgentPanelItem[]
  onCreate: () => void
  onEdit: (itemId: string) => void
  onOpen: (itemId: string) => void
  onRemove: (itemId: string) => void
}) {
  return (
    <section className="space-y-3">
      <div>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-medium">서브 에이전트</h2>
          <button
            type="button"
            onClick={onCreate}
            className="border-border hover:bg-accent/50 inline-flex items-center gap-1.5 border px-2.5 py-1.5 text-xs font-medium transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            추가
          </button>
        </div>
        <p className="text-muted-foreground mt-1 text-xs">
          이 세션에서 CEO가 호출할 수 있는 에이전트를 구성합니다.
        </p>
      </div>

      <div className="border-border border">
        {agentPanels.length === 0 ? (
          <p className="text-muted-foreground px-4 py-3 text-sm">
            에이전트가 없습니다. 추가 버튼으로 역할을 나눌 수 있습니다.
          </p>
        ) : (
          agentPanels.map((item) => (
            <div
              key={item.id}
              className="group/agent border-border hover:bg-accent/50 flex items-center gap-3 border-b px-4 py-2 text-sm transition-colors last:border-b-0"
            >
              <button
                type="button"
                onClick={() => onOpen(item.id)}
                className="flex min-w-0 flex-1 items-center gap-3 text-left"
              >
                <SubAgentProfileImage
                  accent={item.agent.accent}
                  profileImage={item.agent.profileImage}
                  spriteId={item.agent.spriteId}
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{item.agent.name}</span>
                  {item.agent.title && (
                    <span className="text-muted-foreground mt-0.5 block truncate text-xs">
                      {item.agent.title}
                    </span>
                  )}
                  {item.agent.description && (
                    <span className="text-muted-foreground mt-0.5 block truncate text-xs">
                      {item.agent.description}
                    </span>
                  )}
                </span>
                {item.agent.skills?.length ? (
                  <span className="text-muted-foreground hidden shrink-0 text-xs sm:inline">
                    {item.agent.skills.length} skills
                  </span>
                ) : null}
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="text-muted-foreground hover:bg-accent/50 hover:text-foreground pointer-events-none flex h-8 w-8 items-center justify-center opacity-0 transition-opacity group-focus-within/agent:pointer-events-auto group-focus-within/agent:opacity-100 group-hover/agent:pointer-events-auto group-hover/agent:opacity-100 data-[state=open]:pointer-events-auto data-[state=open]:opacity-100"
                    aria-label={`${item.agent.name} 액션`}
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-36">
                  <DropdownMenuItem onClick={() => onEdit(item.id)}>
                    <Pencil className="size-4" />
                    <span>Configuration</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    onClick={() => onRemove(item.id)}
                  >
                    <Trash2 className="size-4" />
                    <span>삭제</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
