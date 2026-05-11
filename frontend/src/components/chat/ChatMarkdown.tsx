import { useMemo, useState, type ComponentPropsWithoutRef, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy } from 'lucide-react'

type ChatMarkdownProps = {
  content: string
}

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: LinkRenderer,
        blockquote: ({ children }) => (
          <blockquote className="border-border text-muted-foreground my-3 border-l-2 pl-3">
            {children}
          </blockquote>
        ),
        code: CodeRenderer,
        h1: ({ children }) => <h1 className="mt-5 mb-2 text-lg font-semibold">{children}</h1>,
        h2: ({ children }) => <h2 className="mt-4 mb-2 text-base font-semibold">{children}</h2>,
        h3: ({ children }) => <h3 className="mt-3 mb-1.5 text-sm font-semibold">{children}</h3>,
        hr: () => <hr className="border-border my-4" />,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
        p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0">{children}</p>,
        pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
        table: ({ children }) => (
          <div className="border-border my-3 max-w-full overflow-x-auto rounded-md border">
            <table className="w-full min-w-max border-collapse text-left text-xs">{children}</table>
          </div>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        td: ({ children }) => (
          <td className="border-border border-t px-3 py-2 align-top [overflow-wrap:anywhere]">
            {children}
          </td>
        ),
        th: ({ children }) => (
          <th className="bg-muted/60 border-border border-b px-3 py-2 font-semibold [overflow-wrap:anywhere]">
            {children}
          </th>
        ),
        thead: ({ children }) => <thead>{children}</thead>,
        ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

function LinkRenderer({ children, href }: ComponentPropsWithoutRef<'a'>) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-primary underline underline-offset-2"
    >
      {children}
    </a>
  )
}

function CodeRenderer({
  children,
  className,
}: ComponentPropsWithoutRef<'code'> & { inline?: boolean }) {
  const language = /language-(\w+)/.exec(className ?? '')?.[1]
  return (
    <code
      className={
        language ? 'font-mono text-xs' : 'bg-muted rounded px-1.5 py-0.5 font-mono text-[0.85em]'
      }
    >
      {children}
    </code>
  )
}

// ─── 코드 블록 — 복사 버튼 포함 ──────────────────────────────

function CodeBlock({ children }: { children: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const text = useMemo(() => extractText(children), [children])

  const handleCopy = async () => {
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // 클립보드 권한이 없거나 사용 불가 — 조용히 무시
    }
  }

  return (
    <div className="group relative my-3">
      <pre className="bg-muted border-border max-w-full overflow-x-auto rounded-md border px-3 py-2 pr-14 text-xs leading-5 dark:border-white/10 dark:bg-white/4">
        {children}
      </pre>
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? '복사됨' : '코드 복사'}
        className={
          // 라이트 모드 스타일
          'absolute top-1.5 right-1.5 inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium ' +
          'border-border bg-background/85 text-muted-foreground hover:bg-background hover:text-foreground backdrop-blur-sm ' +
          // 다크 모드 스타일 (별도 토큰)
          'dark:border-white/15 dark:bg-white/8 dark:text-white/75 dark:hover:bg-white/14 dark:hover:text-white ' +
          // 인터랙션
          'focus-visible:ring-ring transition-colors focus-visible:ring-2 focus-visible:outline-none ' +
          (copied
            ? 'border-emerald-500/40 text-emerald-600 dark:border-emerald-400/40 dark:text-emerald-300'
            : '')
        }
      >
        {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        <span>{copied ? '복사됨' : '복사'}</span>
      </button>
    </div>
  )
}

/** React children 트리에서 순수 텍스트만 재귀적으로 추출 */
function extractText(node: ReactNode): string {
  if (node === null || node === undefined || node === false || node === true) return ''
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: ReactNode } }).props
    return extractText(props?.children)
  }
  return ''
}
