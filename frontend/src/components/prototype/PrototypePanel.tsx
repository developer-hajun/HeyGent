import {
  SandpackCodeEditor,
  SandpackFileExplorer,
  SandpackLayout,
  SandpackPreview,
  SandpackProvider,
  type SandpackFiles,
} from '@codesandbox/sandpack-react'
import { Code2, Eye, Loader2, RefreshCw, X } from 'lucide-react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { getActivePrototypeArtifact, type PrototypeArtifact } from '@/apis/prototypes'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

type PrototypePanelProps = {
  sessionId: string
  openHint: boolean
  reopenSignal?: number
  onArtifactVisible?: () => void
}

type LoadState = 'idle' | 'loading' | 'ready' | 'error'
type PrototypeTab = 'preview' | 'code'

const MIN_PROTOTYPE_PANEL_WIDTH = 480
const MAX_PROTOTYPE_PANEL_WIDTH = 1040

export function PrototypePanel({
  sessionId,
  openHint,
  reopenSignal,
  onArtifactVisible,
}: PrototypePanelProps) {
  const [artifact, setArtifact] = useState<PrototypeArtifact | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [dismissedArtifact, setDismissedArtifact] = useState<{
    versionId: string
    reopenSignal?: number
  } | null>(null)
  const [previewKey, setPreviewKey] = useState(0)
  const [activeTab, setActiveTab] = useState<PrototypeTab>('preview')
  const [panelWidth, setPanelWidth] = useState(() => getInitialPanelWidth())
  const notifiedVersionIdRef = useRef<string | null>(null)
  const shouldPoll = openHint && artifact === null

  useEffect(() => {
    let cancelled = false

    const load = async (showLoading: boolean) => {
      if (showLoading) setLoadState('loading')
      try {
        const response = await getActivePrototypeArtifact(sessionId)
        if (cancelled) return
        setArtifact(response.artifact)
        setLoadState('ready')
        setErrorMessage(null)
        if (response.artifact && notifiedVersionIdRef.current !== response.artifact.versionId) {
          notifiedVersionIdRef.current = response.artifact.versionId
          onArtifactVisible?.()
        }
      } catch (error) {
        if (cancelled) return
        setLoadState('error')
        setErrorMessage(
          error instanceof Error ? error.message : '프로토타입을 불러오지 못했습니다.',
        )
      }
    }

    void load(true)
    const intervalId = shouldPoll
      ? window.setInterval(() => {
          void load(false)
        }, 2500)
      : undefined

    return () => {
      cancelled = true
      if (intervalId !== undefined) window.clearInterval(intervalId)
    }
  }, [onArtifactVisible, sessionId, shouldPoll])

  const visible = Boolean(openHint || artifact)
  const dismissed =
    artifact?.versionId !== undefined &&
    dismissedArtifact?.versionId === artifact.versionId &&
    dismissedArtifact.reopenSignal === reopenSignal

  if (!visible || dismissed) {
    return null
  }

  const title = artifact?.title ?? '프로토타입 생성 중'
  const presetLabel = artifact?.designPresetId ?? 'DESIGN.md'
  const handleResizeStart = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault()
    const startX = event.clientX
    const startWidth = panelWidth
    const previousCursor = document.body.style.cursor
    const previousUserSelect = document.body.style.userSelect

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const handlePointerMove = (moveEvent: PointerEvent) => {
      const maxWidth =
        typeof window === 'undefined'
          ? MAX_PROTOTYPE_PANEL_WIDTH
          : Math.min(
              MAX_PROTOTYPE_PANEL_WIDTH,
              Math.max(MIN_PROTOTYPE_PANEL_WIDTH, window.innerWidth - 360),
            )
      const nextWidth = startWidth + startX - moveEvent.clientX
      setPanelWidth(Math.min(maxWidth, Math.max(MIN_PROTOTYPE_PANEL_WIDTH, nextWidth)))
    }

    const handlePointerUp = () => {
      document.body.style.cursor = previousCursor
      document.body.style.userSelect = previousUserSelect
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }

  return (
    <aside
      className="border-border bg-background relative flex h-full min-h-0 shrink-0 flex-col self-stretch overflow-hidden border-l"
      style={{ width: panelWidth }}
    >
      <div
        role="separator"
        aria-label="프로토타입 패널 너비 조절"
        className="hover:bg-primary/40 absolute top-0 left-0 z-10 h-full w-1 cursor-col-resize bg-transparent transition-colors"
        onPointerDown={handleResizeStart}
      />
      <header className="border-border flex h-12 items-center gap-2 border-b px-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <span className="text-foreground truncate text-sm font-semibold">{title}</span>
            <span className="bg-muted text-muted-foreground shrink-0 rounded-md px-1.5 py-0.5 text-[11px]">
              {presetLabel}
            </span>
          </div>
          <p className="text-muted-foreground truncate text-[11px]">
            {artifact?.summary ?? 'DESIGN.md를 읽고 React 화면 코드를 구성하고 있습니다.'}
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="프리뷰 새로고침"
          onClick={() => setPreviewKey((value) => value + 1)}
          disabled={!artifact}
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="프로토타입 패널 닫기"
          onClick={() =>
            setDismissedArtifact({ versionId: artifact?.versionId ?? 'pending', reopenSignal })
          }
        >
          <X className="h-4 w-4" />
        </Button>
      </header>

      {artifact ? (
        <PrototypeSandpack
          key={`${artifact.versionId}:${previewKey}`}
          activeTab={activeTab}
          artifact={artifact}
          onTabChange={setActiveTab}
        />
      ) : (
        <PrototypeLoading loadState={loadState} errorMessage={errorMessage} />
      )}
    </aside>
  )
}

function PrototypeSandpack({
  activeTab,
  artifact,
  onTabChange,
}: {
  activeTab: PrototypeTab
  artifact: PrototypeArtifact
  onTabChange: (value: PrototypeTab) => void
}) {
  const files = useMemo(() => buildSandpackFiles(artifact), [artifact])

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#0b1020] [&_.cm-content]:!text-slate-100 [&_.cm-editor]:!h-full [&_.cm-editor]:!bg-[#0b1020] [&_.cm-gutters]:!border-slate-800 [&_.cm-gutters]:!bg-[#0b1020] [&_.cm-gutters]:!text-slate-500 [&_.cm-line]:!text-slate-100 [&_.cm-scroller]:!h-full [&_.sp-code-editor]:!h-full [&_.sp-code-editor]:!bg-[#0b1020] [&_.sp-file-explorer]:!h-full [&_.sp-file-explorer]:!bg-[#0f172a] [&_.sp-file-explorer]:!text-slate-200 [&_.sp-layout]:!h-full [&_.sp-layout]:!bg-[#0b1020] [&_.sp-preview]:!h-full [&_.sp-preview-container]:!h-full [&_.sp-stack]:!h-full [&_.sp-wrapper]:!h-full [&_iframe]:!h-full">
      <SandpackProvider
        files={files}
        template="react"
        theme="dark"
        customSetup={{
          dependencies: {
            '@vitejs/plugin-react': '4.3.4',
            'lucide-react': '0.468.0',
            motion: '12.23.24',
            recharts: '2.12.7',
          },
          devDependencies: {
            typescript: '5.6.3',
            vite: '5.4.11',
          },
        }}
        options={{
          activeFile: artifact.entryFile || '/src/App.tsx',
          visibleFiles: Object.keys(files).filter((path) => path.startsWith('/src/')),
        }}
      >
        <Tabs
          value={activeTab}
          onValueChange={(value) => onTabChange(value as PrototypeTab)}
          className="flex h-full min-h-0 flex-1 flex-col"
        >
          <div className="border-border bg-background flex h-10 shrink-0 items-center justify-between border-b px-3">
            <TabsList className="dark:bg-muted dark:text-muted-foreground h-8 bg-slate-200 text-slate-700">
              <TabsTrigger
                value="preview"
                className="dark:data-[state=active]:!bg-background dark:data-[state=active]:!text-foreground h-7 gap-1.5 px-2 text-xs data-[state=active]:!bg-white data-[state=active]:!text-slate-950"
              >
                <Eye className="h-3.5 w-3.5" />
                Preview
              </TabsTrigger>
              <TabsTrigger
                value="code"
                className="dark:data-[state=active]:!bg-background dark:data-[state=active]:!text-foreground h-7 gap-1.5 px-2 text-xs data-[state=active]:!bg-white data-[state=active]:!text-slate-950"
              >
                <Code2 className="h-3.5 w-3.5" />
                Code
              </TabsTrigger>
            </TabsList>
            <span className="text-muted-foreground text-[11px]">v{artifact.versionNumber}</span>
          </div>
          <TabsContent forceMount value="preview" className="m-0 min-h-0 flex-1 overflow-hidden">
            <SandpackLayout className="h-full min-h-0 !rounded-none !border-0">
              <SandpackPreview
                className="h-full min-h-0"
                showNavigator
                showOpenInCodeSandbox={false}
                showRefreshButton
              />
            </SandpackLayout>
          </TabsContent>
          <TabsContent forceMount value="code" className="m-0 min-h-0 flex-1 overflow-hidden">
            <SandpackLayout className="h-full min-h-0 !rounded-none !border-0">
              <SandpackFileExplorer className="h-full min-w-48 shrink-0" />
              <SandpackCodeEditor
                className="h-full min-h-0 flex-1"
                showLineNumbers
                showTabs
                closableTabs
              />
            </SandpackLayout>
          </TabsContent>
        </Tabs>
      </SandpackProvider>
    </div>
  )
}

function PrototypeLoading({
  errorMessage,
  loadState,
}: {
  errorMessage: string | null
  loadState: LoadState
}) {
  if (loadState === 'error') {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-6">
        <div className="border-border bg-card max-w-sm rounded-lg border p-4 text-sm">
          <p className="text-foreground font-medium">프로토타입을 불러오지 못했습니다</p>
          <p className="text-muted-foreground mt-2 leading-6">{errorMessage}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <div className="text-muted-foreground flex items-center gap-2 text-xs">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        디자인 컨텍스트와 React 컴포넌트를 준비하는 중입니다.
      </div>
      <Skeleton className="h-9 w-full rounded-md" />
      <div className="grid flex-1 grid-cols-[180px_minmax(0,1fr)] gap-3">
        <Skeleton className="h-full rounded-md" />
        <div className="space-y-3">
          <Skeleton className="h-20 rounded-md" />
          <Skeleton className="h-32 rounded-md" />
          <Skeleton className="h-28 rounded-md" />
        </div>
      </div>
    </div>
  )
}

function buildSandpackFiles(artifact: PrototypeArtifact): SandpackFiles {
  const baseFiles: SandpackFiles = {
    '/package.json': {
      code: JSON.stringify(
        {
          scripts: { dev: 'vite --host 0.0.0.0' },
          dependencies: {
            '@vitejs/plugin-react': '4.3.4',
            vite: '5.4.11',
            typescript: '5.6.3',
            react: '18.2.0',
            'react-dom': '18.2.0',
            'lucide-react': '0.468.0',
            motion: '12.23.24',
            recharts: '2.12.7',
          },
          devDependencies: {},
        },
        null,
        2,
      ),
    },
    '/index.html': {
      code: '<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0" /></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>',
    },
    '/src/main.tsx': {
      code: "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport './styles.css';\nimport App from './App';\n\ncreateRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);\n",
    },
    '/src/App.tsx': {
      code: 'export default function App() {\n  return <main className="prototype-empty">프로토타입 코드가 아직 없습니다.</main>;\n}\n',
    },
    '/src/styles.css': {
      code: 'body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; } .prototype-empty { min-height: 100vh; display: grid; place-items: center; color: #64748b; }',
    },
  }

  return {
    ...baseFiles,
    ...Object.fromEntries(
      Object.entries(artifact.files).map(([path, file]) => [
        normalizeSandpackPath(path),
        { code: file.code },
      ]),
    ),
  }
}

function normalizeSandpackPath(path: string) {
  const normalized = path.replaceAll('\\', '/').trim()
  return normalized.startsWith('/') ? normalized : `/${normalized}`
}

function getInitialPanelWidth() {
  if (typeof window === 'undefined') return 760
  return Math.min(
    MAX_PROTOTYPE_PANEL_WIDTH,
    Math.max(MIN_PROTOTYPE_PANEL_WIDTH, Math.round(window.innerWidth * 0.5)),
  )
}
