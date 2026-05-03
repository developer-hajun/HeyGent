import { Loader2, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useTaskRunStore } from '@/store/useTaskRunStore'
import type { RawApproval } from '@/types/taskRuns'
import { toApprovalStatusText } from './activityPanelText'

export function ApprovalCard({
  approval,
  taskRunId,
}: {
  approval: RawApproval
  taskRunId: string
}) {
  const resumeTaskRun = useTaskRunStore((state) => state.resumeTaskRun)
  const cancelTaskRun = useTaskRunStore((state) => state.cancelTaskRun)
  const isApprovalSubmitting = useTaskRunStore((state) =>
    state.isApprovalSubmitting(approval.approval_id),
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const isActionable =
    approval.status === undefined || approval.status === null || approval.status === 'PENDING'
  const isButtonDisabled = isSubmitting || isApprovalSubmitting

  const handleResume = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await resumeTaskRun({
        taskRunId,
        approvalId: approval.approval_id,
        decision: 'APPROVED',
        response: { approved: true },
      })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '승인 응답 전송에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await resumeTaskRun({
        taskRunId,
        approvalId: approval.approval_id,
        decision: 'REJECTED',
        response: { approved: false },
      })
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '거절 응답 전송에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancel = async () => {
    if (!isActionable || isButtonDisabled) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      await cancelTaskRun(taskRunId, 'approval cancelled from UI')
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'TaskRun 취소에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="border-border bg-card rounded-lg border p-3">
      <div className="flex items-start gap-3">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
        <div className="min-w-0 flex-1">
          <h3 className="text-foreground text-sm font-semibold">
            {approval.title ?? '확인이 필요합니다'}
          </h3>
          {approval.description && (
            <p className="text-muted-foreground mt-1 text-xs leading-5">{approval.description}</p>
          )}
          <p className="text-muted-foreground mt-2 text-[11px]">
            approval {approval.approval_id} · {toApprovalStatusText(approval.status)}
          </p>
        </div>
      </div>
      {errorMessage && <p className="text-destructive mt-3 text-xs">{errorMessage}</p>}
      {isActionable && (
        <div className="mt-3 flex gap-2">
          <Button
            type="button"
            size="sm"
            onClick={handleResume}
            disabled={isButtonDisabled}
            aria-label={`Approval ${approval.approval_id} 승인 후 TaskRun 재개`}
          >
            {isButtonDisabled ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            승인
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleReject}
            disabled={isButtonDisabled}
            aria-label={`Approval ${approval.approval_id} 거절 후 TaskRun 재개`}
          >
            거절
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleCancel}
            disabled={isButtonDisabled}
            aria-label={`TaskRun ${taskRunId} 취소`}
          >
            작업 취소
          </Button>
        </div>
      )}
    </section>
  )
}
