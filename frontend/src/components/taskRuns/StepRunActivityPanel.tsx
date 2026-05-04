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
  onFocusTaskRunMessage?: (taskRunId: string) => void
}

export function StepRunActivityPanel({
  open,
  onOpenChange,
  sessionId,
  selectedTaskRunId,
  onSelectTaskRun,
  onFocusTaskRunMessage,
}: StepRunActivityPanelProps) {
  const isDesktop = useIsDesktopViewport()

  // 같은 진행 상황 본문을 화면 크기에 따라 다른 껍데기로 보여준다.
  // 데스크톱은 대화 옆 고정 패널, 모바일은 하단에서 올라오는 Drawer가 자연스럽다.
  return (
    <>
      {open && isDesktop && (
        <aside className="border-border bg-popover hidden w-96 shrink-0 flex-col border-l lg:flex">
          <StepRunActivityPanelBody
            sessionId={sessionId}
            selectedTaskRunId={selectedTaskRunId}
            onSelectTaskRun={onSelectTaskRun}
            onFocusTaskRunMessage={onFocusTaskRunMessage}
            onClose={() => onOpenChange(false)}
          />
        </aside>
      )}
      {!isDesktop && (
        <Drawer open={open} onOpenChange={onOpenChange} direction="bottom">
          <DrawerContent className="bg-popover max-h-[86vh] p-0">
            <DrawerHeader className="sr-only">
              <DrawerTitle>답변 활동</DrawerTitle>
              <DrawerDescription>이 세션의 답변 진행 단계와 세부 기록입니다.</DrawerDescription>
            </DrawerHeader>
            <StepRunActivityPanelBody
              sessionId={sessionId}
              selectedTaskRunId={selectedTaskRunId}
              onSelectTaskRun={onSelectTaskRun}
              onFocusTaskRunMessage={onFocusTaskRunMessage}
              onClose={() => onOpenChange(false)}
            />
          </DrawerContent>
        </Drawer>
      )}
    </>
  )
}
