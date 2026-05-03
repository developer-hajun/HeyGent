import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'
import { StepRunActivityPanelBody } from './stepRunActivityPanel/StepRunActivityPanelBody'
import { useIsDesktopViewport } from './stepRunActivityPanel/useIsDesktopViewport'

type StepRunActivityPanelProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  selectedTaskRunId?: string
  onSelectTaskRun: (taskRunId: string | undefined) => void
}

export function StepRunActivityPanel({
  open,
  onOpenChange,
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
}: StepRunActivityPanelProps) {
  const isDesktop = useIsDesktopViewport()

  return (
    <>
      {open && isDesktop && (
        <aside className="border-border bg-popover hidden w-96 shrink-0 flex-col border-l lg:flex">
          <StepRunActivityPanelBody
            sessionId={sessionId}
            selectedTaskRunId={selectedTaskRunId}
            onSelectTaskRun={onSelectTaskRun}
            onClose={() => onOpenChange(false)}
          />
        </aside>
      )}
      {!isDesktop && (
        <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
          <DrawerContent className="bg-popover max-h-[86vh] p-0">
            <DrawerHeader className="sr-only">
              <DrawerTitle>진행 상황</DrawerTitle>
              <DrawerDescription>현재 답변의 진행 단계와 세부 기록입니다.</DrawerDescription>
            </DrawerHeader>
            <StepRunActivityPanelBody
              sessionId={sessionId}
              selectedTaskRunId={selectedTaskRunId}
              onSelectTaskRun={onSelectTaskRun}
              onClose={() => onOpenChange(false)}
            />
          </DrawerContent>
        </Drawer>
      )}
    </>
  )
}
