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
  // 서버 payload에서 status가 비어 오면 아직 응답하지 않은 확인 요청으로 본다.
  const isActionable =
    approval.status === undefined || approval.status === null || approval.status === 'PENDING'
  const isButtonDisabled = isSubmitting || isApprovalSubmitting

  // 승인/거절은 TaskRun을 다시 진행시키는 resume 명령이고, 작업 취소는 실행 자체를 중단한다.
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
      console.error(error)
      setErrorMessage('확인 응답을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.')
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
      console.error(error)
      setErrorMessage('확인 응답을 보내지 못했습니다. 잠시 후 다시 시도해 주세요.')
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
      console.error(error)
      setErrorMessage('답변 준비를 취소하지 못했습니다. 잠시 후 다시 시도해 주세요.')
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
            확인 요청 · {toApprovalStatusText(approval.status)}
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
            aria-label="확인 요청 승인"
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
            aria-label="확인 요청 거절"
          >
            거절
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleCancel}
            disabled={isButtonDisabled}
            aria-label="답변 준비 취소"
          >
            작업 취소
          </Button>
        </div>
      )}
    </section>
  )
}
