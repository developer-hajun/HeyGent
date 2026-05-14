export function shouldHydrateTaskRunOnSessionOpen({
  hasRuntimeState,
  isLatestMessageTaskRun,
}: {
  hasRuntimeState: boolean
  isLatestMessageTaskRun: boolean
}) {
  return hasRuntimeState || isLatestMessageTaskRun
}
