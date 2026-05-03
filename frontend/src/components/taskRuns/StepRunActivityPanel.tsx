import { CheckCircle2, Clock3, Loader2, XCircle } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import type { ActivityItemView } from '@/components/chat/chatTypes'

type StepRunActivityPanelProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  items: ActivityItemView[]
}

export function StepRunActivityPanel({
  open,
  onOpenChange,
  sessionId,
  items,
}: StepRunActivityPanelProps) {
  return (
    <>
      {open && (
        <aside className="border-border bg-popover hidden w-80 shrink-0 flex-col border-l lg:flex">
          <PanelBody sessionId={sessionId} items={items} />
        </aside>
      )}
      <div className="lg:hidden">
        <Sheet open={open} onOpenChange={onOpenChange}>
          <SheetContent side="right" className="bg-popover w-[88vw] p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>작업 활동</SheetTitle>
              <SheetDescription>현재 세션의 TaskRun과 StepRun 활동입니다.</SheetDescription>
            </SheetHeader>
            <PanelBody sessionId={sessionId} items={items} />
          </SheetContent>
        </Sheet>
      </div>
    </>
  )
}

function PanelBody({ sessionId, items }: { sessionId: string; items: ActivityItemView[] }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-border border-b p-4">
        <p className="text-muted-foreground text-xs">세션 {sessionId}</p>
        <h2 className="text-foreground mt-1 text-sm font-semibold">작업 활동</h2>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-4 text-sm leading-6">
            아직 표시할 활동이 없습니다. assistant 응답이 시작되면 StepRun 상태가 여기에 쌓입니다.
          </div>
        ) : (
          <ol className="space-y-3">
            {items.map((item) => (
              <li key={item.id} className="bg-card border-border rounded-lg border p-3">
                <div className="flex items-start gap-3">
                  <ActivityIcon tone={item.tone} />
                  <div className="min-w-0 flex-1">
                    <p className="text-foreground text-sm font-medium">{item.title}</p>
                    <p className="text-muted-foreground mt-1 text-xs leading-5">
                      {item.statusText}
                    </p>
                    {item.occurredAt && (
                      <p className="text-muted-foreground/80 mt-2 text-[11px]">{item.occurredAt}</p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}

function ActivityIcon({ tone }: { tone: ActivityItemView['tone'] }) {
  if (tone === 'completed')
    return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
  if (tone === 'failed') return <XCircle className="text-destructive mt-0.5 h-4 w-4 shrink-0" />
  if (tone === 'waiting') return <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
  return <Loader2 className="text-primary mt-0.5 h-4 w-4 shrink-0 animate-spin" />
}
