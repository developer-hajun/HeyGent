import { CheckCircle2, CircleHelp, Clock3, FileText, Loader2, XCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { cn } from '@/components/ui/utils'
import type { TaskRunStatusTone } from '@/types/taskRuns'

const STATUS_TONE_VIEW: Record<
  TaskRunStatusTone,
  {
    label: string
    description: string
    iconClassName: string
    badgeClassName: string
  }
> = {
  running: {
    label: '진행 중',
    description: 'AI가 답변을 만들거나 도구를 실행하고 있습니다.',
    iconClassName: 'text-primary',
    badgeClassName: 'border-primary/20 bg-primary/10 text-primary',
  },
  waiting: {
    label: '확인 필요',
    description: '사용자 확인, 승인, 추가 정보가 필요해 멈춰 있습니다.',
    iconClassName: 'text-amber-500',
    badgeClassName: 'border-amber-500/20 bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  completed: {
    label: '완료',
    description: '해당 답변, 단계, 도구 실행이 정상적으로 끝났습니다.',
    iconClassName: 'text-emerald-500',
    badgeClassName:
      'border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  },
  failed: {
    label: '실패',
    description: '오류가 발생했거나 요청이 취소되었습니다.',
    iconClassName: 'text-destructive',
    badgeClassName: 'border-destructive/20 bg-destructive/10 text-destructive',
  },
  idle: {
    label: '기록',
    description: '상태가 확정되지 않은 일반 기록입니다.',
    iconClassName: 'text-muted-foreground',
    badgeClassName: 'border-border bg-muted text-muted-foreground',
  },
}

export function TaskRunStatusIcon({ tone }: { tone: TaskRunStatusTone }) {
  const view = STATUS_TONE_VIEW[tone]
  if (tone === 'completed')
    return <CheckCircle2 className={cn('mt-0.5 h-4 w-4 shrink-0', view.iconClassName)} />
  if (tone === 'failed')
    return <XCircle className={cn('mt-0.5 h-4 w-4 shrink-0', view.iconClassName)} />
  if (tone === 'waiting')
    return <Clock3 className={cn('mt-0.5 h-4 w-4 shrink-0', view.iconClassName)} />
  if (tone === 'running') {
    return <Loader2 className={cn('mt-0.5 h-4 w-4 shrink-0 animate-spin', view.iconClassName)} />
  }
  return <FileText className={cn('mt-0.5 h-4 w-4 shrink-0', view.iconClassName)} />
}

export function TaskRunStatusBadge({
  tone,
  label,
  className,
}: {
  tone: TaskRunStatusTone
  label?: string
  className?: string
}) {
  const view = STATUS_TONE_VIEW[tone]
  return (
    <span
      className={cn(
        'inline-flex h-6 max-w-full items-center gap-1.5 rounded-md border px-2 text-[11px] font-medium',
        view.badgeClassName,
        className,
      )}
    >
      <TaskRunStatusIcon tone={tone} />
      <span className="truncate">{label ?? view.label}</span>
    </span>
  )
}

export function TaskRunStatusLegend() {
  const items: TaskRunStatusTone[] = ['running', 'waiting', 'completed', 'failed']

  return (
    <div className="border-border bg-muted/20 mt-3 rounded-lg border px-3 py-2">
      <div className="text-muted-foreground mb-2 text-[11px] font-medium">상태 기준</div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((tone) => (
          <TaskRunStatusBadge key={tone} tone={tone} />
        ))}
      </div>
    </div>
  )
}

export function TaskRunStatusHelpDialog() {
  const items: TaskRunStatusTone[] = ['running', 'waiting', 'completed', 'failed', 'idle']

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label="답변 활동 상태 설명"
          className="border-border bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground flex h-7 shrink-0 items-center gap-1.5 rounded-md border px-2 text-[11px] font-medium transition-colors"
        >
          <CircleHelp className="h-4 w-4" />
          <span>상태 설명</span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">답변 활동 상태</DialogTitle>
          <DialogDescription>
            색과 아이콘은 실행 주체가 아니라 현재 상태를 나타냅니다.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {items.map((tone) => {
            const view = STATUS_TONE_VIEW[tone]
            return (
              <div key={tone} className="flex items-start gap-3">
                <TaskRunStatusBadge tone={tone} />
                <p className="text-muted-foreground min-w-0 flex-1 text-sm leading-6">
                  {view.description}
                </p>
              </div>
            )
          })}
        </div>
        <div className="border-border bg-muted/30 text-muted-foreground rounded-lg border p-3 text-xs leading-5">
          에이전트 구분은 이름과 배지로 표시합니다. 세부 기록의 도구 입력, 도구 결과, 원본 이벤트는
          실행을 추적하기 위한 개발자 기록입니다.
        </div>
      </DialogContent>
    </Dialog>
  )
}
