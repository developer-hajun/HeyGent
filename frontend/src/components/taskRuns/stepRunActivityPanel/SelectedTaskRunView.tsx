import { RotateCcw } from 'lucide-react'
import type { ActivityItemView, RawApproval, RawStepRun, RawTaskRun } from '@/types/taskRuns'
import { toTaskRunStatusTone } from '@/utils/taskRunStatusView'
import { isTerminalTaskRunStatus, resolveTaskRunDisplayStatus } from '@/utils/taskRunDisplayStatus'
import { ActivityEventItem } from './ActivityEventItem'
import { ApprovalCard } from './ApprovalCard'
import { StepProgressItem } from './StepProgressItem'
import { toStepProgressSentence, toUserFacingTaskTitle } from './activityPanelText'
import { TaskRunStatusBadge, TaskRunStatusIcon } from './TaskRunStatusIcon'

export function SelectedTaskRunView({
  taskRunId,
  taskRun,
  steps,
  approvals,
  activities,
  replayNeeded,
}: {
  taskRunId: string
  taskRun?: RawTaskRun
  prompt?: string
  steps: RawStepRun[]
  approvals: RawApproval[]
  activities: ActivityItemView[]
  replayNeeded: boolean
}) {
  // snapshot이 아직 도착하지 않은 순간에는 raw event의 마지막 상태를 대표 상태로 쓴다.
  const status = resolveTaskRunDisplayStatus(taskRun, activities)
  const taskRunFinished = isTerminalTaskRunStatus(status)
  const reversedActivities = [...activities].reverse()
  const agentNameMap = buildActivityAgentNameMap(activities)
  const currentStep = selectCurrentVisibleStep(taskRun, steps)
  const memoryDebug = buildMemoryDebugView(taskRun)
  const currentStepTone = toTaskRunStatusTone(currentStep?.status ?? status)

  return (
    <div className="selectable-text space-y-5">
      {!taskRunFinished && currentStep !== undefined && (
        <section className="border-border bg-muted/30 rounded-lg border px-3 py-2">
          <div className="flex items-start gap-2">
            <TaskRunStatusIcon tone={currentStepTone} />
            <div className="min-w-0">
              <div className="text-foreground line-clamp-1 text-xs font-semibold [overflow-wrap:anywhere] break-words">
                {toUserFacingTaskTitle(currentStep.title ?? currentStep.goal ?? '답변 진행')}
              </div>
              <TaskRunStatusBadge
                tone={currentStepTone}
                label={toStepProgressSentence(currentStep.status ?? status)}
                className="mt-1"
              />
            </div>
          </div>
        </section>
      )}

      {replayNeeded && (
        <section className="border-border bg-muted/40 text-muted-foreground flex items-center gap-2 rounded-lg border px-3 py-2 text-xs">
          <RotateCcw className="h-3.5 w-3.5" />
          진행 기록 일부를 다시 불러와야 합니다.
        </section>
      )}

      {approvals.map((approval) => (
        <ApprovalCard key={approval.approval_id} approval={approval} taskRunId={taskRunId} />
      ))}

      <section>
        <h3 className="text-foreground mb-2 text-xs font-semibold">진행 단계</h3>
        {steps.length === 0 ? (
          <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
            아직 세부 단계가 없습니다.
          </div>
        ) : (
          <ol className="space-y-2">
            {steps.map((step) => (
              <StepProgressItem
                key={step.step_run_id}
                step={step}
                activities={activities.filter(
                  (activity) => activity.stepRunId === step.step_run_id,
                )}
                allActivities={activities}
              />
            ))}
          </ol>
        )}
      </section>

      <section>
        <details className="group">
          <summary className="text-foreground hover:bg-muted flex cursor-pointer list-none items-center justify-between rounded-lg px-2 py-2 text-xs font-semibold transition-colors">
            <span>장기기억 디버그</span>
            <span className="text-muted-foreground text-[11px]">{memoryDebug.summary}</span>
          </summary>
          <div className="border-border bg-muted/20 mt-2 space-y-3 rounded-lg border p-3">
            <MemoryDebugBlock title="Recall" value={memoryDebug.recall} />
            <MemoryDebugBlock title="Writeback" value={memoryDebug.writeback} />
            <MemoryDebugBlock title="Mark Used" value={memoryDebug.markUsed} />
            <MemoryDebugBlock title="Context" value={memoryDebug.context} />
            <details>
              <summary className="text-muted-foreground hover:text-foreground cursor-pointer text-[11px] font-medium">
                Raw memory payload
              </summary>
              <pre className="selectable-text bg-background text-muted-foreground border-border mt-2 max-h-72 overflow-auto rounded-md border p-2 text-[11px] leading-relaxed">
                {formatDebugJson(memoryDebug.raw)}
              </pre>
            </details>
          </div>
        </details>
      </section>

      <section>
        <details className="group">
          <summary className="text-foreground hover:bg-muted flex cursor-pointer list-none items-center justify-between rounded-lg px-2 py-2 text-xs font-semibold transition-colors">
            <span>세부 기록</span>
            <span className="text-muted-foreground text-[11px]">{activities.length}개</span>
          </summary>
          {activities.length === 0 ? (
            <div className="text-muted-foreground border-border rounded-lg border border-dashed p-3 text-xs">
              아직 세부 기록이 없습니다.
            </div>
          ) : (
            <ol className="mt-2 space-y-2">
              {reversedActivities.map((activity) => (
                <ActivityEventItem
                  key={activity.id}
                  activity={activity}
                  taskRunFinished={taskRunFinished}
                  agentNameMap={agentNameMap}
                />
              ))}
            </ol>
          )}
        </details>
      </section>
    </div>
  )
}

function MemoryDebugBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div>
      <div className="text-muted-foreground mb-1 text-[11px] font-semibold uppercase">{title}</div>
      <pre className="selectable-text bg-background text-muted-foreground border-border max-h-44 overflow-auto rounded-md border p-2 text-[11px] leading-relaxed">
        {formatDebugJson(value)}
      </pre>
    </div>
  )
}

function selectCurrentVisibleStep(taskRun: RawTaskRun | undefined, steps: RawStepRun[]) {
  const currentStepRunId =
    typeof taskRun?.current_step_run_id === 'string'
      ? taskRun.current_step_run_id
      : typeof taskRun?.currentStepRunId === 'string'
        ? taskRun.currentStepRunId
        : undefined

  if (currentStepRunId !== undefined) {
    const currentStep = steps.find((step) => step.step_run_id === currentStepRunId)
    if (currentStep !== undefined) {
      return currentStep
    }
  }

  return (
    steps.find(
      (step) => step.status === 'RUNNING' || step.status === 'WAITING' || step.status === 'BLOCKED',
    ) ?? steps.at(-1)
  )
}

function buildMemoryDebugView(taskRun: RawTaskRun | undefined) {
  const inputPayload = toRecord(taskRun?.input_payload)
  const resultPayload = toRecord(taskRun?.result_payload)
  const recallMeta = toRecord(toRecord(inputPayload?.memory_context_meta)?.recall)
  const memoryObservation = toRecord(resultPayload?.memory_observation)
  const recallObservation = toRecord(memoryObservation?.recall)
  const writebackObservation = toRecord(memoryObservation?.writeback)
  const markUsedObservation = toRecord(memoryObservation?.mark_used)
  const persistentMemoryContext =
    typeof inputPayload?.persistent_memory_context === 'string'
      ? inputPayload.persistent_memory_context
      : ''

  const recall = {
    inputStatus: recallMeta?.status,
    inputReason: recallMeta?.reason,
    planner: recallMeta?.planner,
    count: recallObservation?.count ?? recallMeta?.count,
    memoryIds: recallObservation?.memory_ids ?? recallMeta?.memory_ids,
    memoryTypes: recallObservation?.memory_types ?? recallMeta?.memory_types,
    storeTypes: recallObservation?.store_types ?? recallMeta?.store_types,
    observationStatus: recallObservation?.status,
    observationReason: recallObservation?.reason,
    failed: recallObservation?.failed ?? recallMeta?.failed,
  }

  const writeback = {
    status: writebackObservation?.status,
    reason: writebackObservation?.reason,
    attempted: writebackObservation?.attempted,
    candidateCount: writebackObservation?.candidate_count,
    memoryTypes: writebackObservation?.memory_types,
    storeTypes: writebackObservation?.store_types,
    scopeTypes: writebackObservation?.scope_types,
    operationTypes: writebackObservation?.operation_types,
    failed: writebackObservation?.failed,
  }

  const markUsed = {
    status: markUsedObservation?.status,
    reason: markUsedObservation?.reason,
    attempted: markUsedObservation?.attempted,
    recalledMemoryIds: markUsedObservation?.recalled_memory_ids,
    usedMemoryIds: markUsedObservation?.used_memory_ids,
    skippedMemoryIds: markUsedObservation?.skipped_memory_ids,
    failedMemoryIds: markUsedObservation?.failed_memory_ids,
    scores: markUsedObservation?.scores,
    attribution: markUsedObservation?.attribution,
    deduplicated: markUsedObservation?.deduplicated,
    failed: markUsedObservation?.failed,
  }

  const context = {
    hasPersistentMemoryContext: persistentMemoryContext.length > 0,
    persistentMemoryContextLength: persistentMemoryContext.length,
    persistentMemoryContextPreview: previewText(persistentMemoryContext),
  }

  return {
    summary: summarizeMemoryDebug(recall, writeback, markUsed, context),
    recall,
    writeback,
    markUsed,
    context,
    raw: {
      memoryContextMeta: inputPayload?.memory_context_meta,
      memoryObservation: resultPayload?.memory_observation,
    },
  }
}

function buildActivityAgentNameMap(activities: ActivityItemView[]) {
  const names = new Map<string, string>()
  activities.forEach((activity) => {
    addAgentRef(names, activity.displayContext?.actorAgent)
    addAgentRef(names, activity.displayContext?.assigneeAgent)
    activity.displayContext?.delegatedAgents?.forEach((agent) => addAgentRef(names, agent))

    const payload = toRecord(activity.raw.payload)
    const input = toRecord(payload?.input) ?? toRecord(payload?.args)
    const result = toRecord(payload?.result) ?? toRecord(payload?.output)
    const agent = toRecord(result?.agent)
    addAgentName(
      names,
      stringValue(agent?.profileId) ??
        stringValue(agent?.profile_id) ??
        stringValue(agent?.agentId) ??
        stringValue(agent?.id) ??
        stringValue(input?.assigneeAgentId),
      stringValue(agent?.name) ?? stringValue(agent?.displayName),
    )
  })
  return names
}

function addAgentRef(
  names: Map<string, string>,
  agent?: { id?: string; profileId?: string | null; displayName?: string },
) {
  addAgentName(names, agent?.id, agent?.displayName)
  addAgentName(names, agent?.profileId ?? undefined, agent?.displayName)
}

function addAgentName(names: Map<string, string>, id?: string, name?: string) {
  if (id === undefined || name === undefined) return
  const normalizedId = id.trim()
  const normalizedName = name.trim()
  if (!normalizedId || !normalizedName || isRawAgentId(normalizedName)) return
  names.set(normalizedId, normalizedName)
}

function isRawAgentId(value: string) {
  return /^agent_profile_[a-z0-9]+$/i.test(value.trim())
}

function summarizeMemoryDebug(
  recall: Record<string, unknown>,
  writeback: Record<string, unknown>,
  markUsed: Record<string, unknown>,
  context: Record<string, unknown>,
) {
  const recallStatus =
    stringValue(recall.observationStatus) ?? stringValue(recall.inputStatus) ?? 'none'
  const writebackStatus = stringValue(writeback.status) ?? 'none'
  const markUsedStatus = stringValue(markUsed.status) ?? 'none'
  const hasContext = context.hasPersistentMemoryContext === true ? 'ctx' : 'no ctx'
  return `recall ${recallStatus} · write ${writebackStatus} · used ${markUsedStatus} · ${hasContext}`
}

function toRecord(value: unknown): Record<string, unknown> | undefined {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return undefined
  }
  return value as Record<string, unknown>
}

function stringValue(value: unknown) {
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : undefined
}

function previewText(value: string) {
  const normalized = value.trim()
  if (normalized.length <= 300) {
    return normalized
  }
  return `${normalized.slice(0, 300)}...`
}

function formatDebugJson(value: unknown) {
  return JSON.stringify(value ?? null, null, 2)
}
