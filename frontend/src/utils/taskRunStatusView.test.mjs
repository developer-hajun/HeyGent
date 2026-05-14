import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdir, rm } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

const rootDir = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const outDir = resolve(rootDir, '../tmp/frontend-node-tests')

async function compileUtilityModules() {
  await rm(outDir, { recursive: true, force: true })
  await mkdir(outDir, { recursive: true })
  execFileSync(
    process.execPath,
    [
      resolve(rootDir, 'node_modules/typescript/bin/tsc'),
      '--ignoreConfig',
      '--target',
      'ES2022',
      '--module',
      'ES2022',
      '--moduleResolution',
      'Bundler',
      '--strict',
      '--skipLibCheck',
      '--outDir',
      outDir,
      'src/utils/taskRunDisplayStatus.ts',
      'src/utils/taskRunHydration.ts',
      'src/utils/chatLiveState.ts',
    ],
    { cwd: rootDir, stdio: 'pipe' },
  )
}

async function importCompiledModule(fileName) {
  await compileUtilityModules()
  return import(`${pathToFileURL(resolve(outDir, fileName)).href}?v=${Date.now()}`)
}

test('terminal TaskRun status wins over stale running activity', async () => {
  const { resolveTaskRunDisplayStatus } = await importCompiledModule('taskRunDisplayStatus.js')

  const status = resolveTaskRunDisplayStatus(
    { status: 'COMPLETED' },
    [{ raw: { status: 'RUNNING', event_type: 'step.started' } }],
  )

  assert.equal(status, 'COMPLETED')
})

test('latest message TaskRun is hydrated after returning to a session', async () => {
  const { shouldHydrateTaskRunOnSessionOpen } = await importCompiledModule('taskRunHydration.js')

  assert.equal(
    shouldHydrateTaskRunOnSessionOpen({
      hasRuntimeState: false,
      isLatestMessageTaskRun: true,
    }),
    true,
  )
  assert.equal(
    shouldHydrateTaskRunOnSessionOpen({
      hasRuntimeState: false,
      isLatestMessageTaskRun: false,
    }),
    false,
  )
})

test('completed assistant message does not keep showing stale waiting progress', async () => {
  const { shouldShowAssistantTaskRunProgress } =
    await importCompiledModule('taskRunDisplayStatus.js')

  assert.equal(
    shouldShowAssistantTaskRunProgress({
      messageStatus: 'completed',
      taskStatus: 'WAITING',
      stepRunCount: 1,
    }),
    false,
  )
})

test('streaming assistant message keeps progress visible even when task status is stale completed', async () => {
  const { shouldShowAssistantTaskRunProgress } =
    await importCompiledModule('taskRunDisplayStatus.js')

  assert.equal(
    shouldShowAssistantTaskRunProgress({
      messageStatus: 'streaming',
      taskStatus: 'COMPLETED',
      stepRunCount: 1,
    }),
    true,
  )
})

test('message reload keeps local live assistant placeholder when server list has not persisted it', async () => {
  const { mergeLiveMessagesIntoPersistedList } = await importCompiledModule('chatLiveState.js')

  const merged = mergeLiveMessagesIntoPersistedList(
    [
      {
        id: 'user-1',
        sessionId: 'session-1',
        role: 'user',
        content: '질문',
        status: 'accepted',
      },
    ],
    [
      {
        id: 'user-1',
        sessionId: 'session-1',
        role: 'user',
        content: '질문',
        status: 'accepted',
      },
      {
        id: 'assistant-task-1',
        sessionId: 'session-1',
        role: 'assistant',
        content: '',
        status: 'waiting',
        taskRunId: 'task-1',
      },
    ],
    'session-1',
  )

  assert.equal(merged.length, 2)
  assert.equal(merged[1].status, 'waiting')
  assert.equal(merged[1].taskRunId, 'task-1')
})

test('completed message without payload status still clears sidebar running state', async () => {
  const { resolveCompletedSessionTaskStatus } = await importCompiledModule('chatLiveState.js')

  assert.equal(resolveCompletedSessionTaskStatus(undefined), 'COMPLETED')
  assert.equal(resolveCompletedSessionTaskStatus('FAILED'), 'FAILED')
})

test('session list reconciliation does not resurrect older running state after local completion', async () => {
  const { reconcileSessionRunState } = await importCompiledModule('chatLiveState.js')

  const reconciled = reconcileSessionRunState(
    {
      session_id: 'session-1',
      active_task_run_id: null,
      last_task_run_status: 'COMPLETED',
      updated_at: '2026-05-14T10:00:10.000Z',
    },
    {
      session_id: 'session-1',
      active_task_run_id: 'task-1',
      last_task_run_status: 'RUNNING',
      updated_at: '2026-05-14T10:00:00.000Z',
    },
  )

  assert.equal(reconciled.active_task_run_id, null)
  assert.equal(reconciled.last_task_run_status, 'COMPLETED')
})

test('persisted completed assistant message clears stale active session run', async () => {
  const { shouldClearSessionRunFromPersistedMessages } =
    await importCompiledModule('chatLiveState.js')

  assert.equal(
    shouldClearSessionRunFromPersistedMessages(
      {
        active_task_run_id: 'task-1',
        last_task_run_status: 'RUNNING',
      },
      [
        {
          id: 'assistant-1',
          sessionId: 'session-1',
          role: 'assistant',
          status: 'completed',
          taskRunId: 'task-1',
        },
      ],
    ),
    true,
  )
})

test('latest completed assistant message clears stale running session even without task id', async () => {
  const { shouldClearSessionRunFromPersistedMessages } =
    await importCompiledModule('chatLiveState.js')

  assert.equal(
    shouldClearSessionRunFromPersistedMessages(
      {
        active_task_run_id: 'task-1',
        last_task_run_status: 'RUNNING',
      },
      [
        {
          id: 'user-1',
          sessionId: 'session-1',
          role: 'user',
          status: 'accepted',
        },
        {
          id: 'assistant-1',
          sessionId: 'session-1',
          role: 'assistant',
          status: 'completed',
        },
      ],
    ),
    true,
  )
})
