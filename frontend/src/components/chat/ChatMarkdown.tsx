import {
  isValidElement,
  useMemo,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from 'react'
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
  const language = getLanguageFromClassName(className)
  return (
    <code
      className={
        language
          ? 'font-mono text-xs'
          : 'bg-muted text-foreground border-border dark:bg-muted/80 rounded border px-1.5 py-0.5 font-mono text-[0.85em]'
      }
      data-language={language}
    >
      {children}
    </code>
  )
}

// ─── 코드 블록 — 복사 버튼 포함 ──────────────────────────────

function CodeBlock({ children }: { children: ReactNode }) {
  const [copied, setCopied] = useState(false)
  const text = useMemo(() => extractText(children), [children])
  const language = useMemo(() => extractLanguage(children), [children])
  const highlightedCode = useMemo(() => highlightCode(text, language), [language, text])

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
      {language && (
        <div className="border-border absolute top-0 right-0 left-0 flex h-8 items-center justify-between border-b px-3">
          <span className="text-muted-foreground font-mono text-[10px] font-medium tracking-wide uppercase">
            {language}
          </span>
        </div>
      )}
      <pre className="max-w-full overflow-x-auto rounded-md border [border-color:var(--syntax-border)] px-3 py-2 pr-14 text-xs leading-5 [color:var(--syntax-foreground)] [background:var(--syntax-background)]">
        <code className={`block min-w-max font-mono ${language ? 'pt-8' : ''}`}>
          {highlightedCode}
        </code>
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

function getLanguageFromClassName(className?: string) {
  return /language-([\w-]+)/.exec(className ?? '')?.[1]?.toLowerCase()
}

function extractLanguage(node: ReactNode): string | undefined {
  if (Array.isArray(node)) {
    return node.map(extractLanguage).find(Boolean)
  }
  if (!isValidElement(node)) return undefined
  const props = node.props as { className?: string; 'data-language'?: string; children?: ReactNode }
  return (
    props['data-language'] ??
    getLanguageFromClassName(props.className) ??
    extractLanguage(props.children)
  )
}

const KEYWORDS = new Set([
  'abstract',
  'and',
  'as',
  'async',
  'await',
  'break',
  'case',
  'catch',
  'class',
  'const',
  'continue',
  'def',
  'default',
  'do',
  'else',
  'enum',
  'export',
  'extends',
  'false',
  'finally',
  'for',
  'from',
  'fun',
  'function',
  'if',
  'implements',
  'import',
  'in',
  'interface',
  'is',
  'let',
  'new',
  'null',
  'object',
  'of',
  'or',
  'package',
  'private',
  'protected',
  'public',
  'return',
  'static',
  'super',
  'switch',
  'this',
  'throw',
  'true',
  'try',
  'type',
  'val',
  'var',
  'void',
  'when',
  'while',
])

const TOKEN_PATTERN =
  /(\/\*[\s\S]*?\*\/|\/\/[^\n]*|#[^\n]*|<!--[\s\S]*?-->|(["'`])(?:\\.|(?!\2)[\s\S])*?\2|<\/?[A-Za-z][\w:.-]*|[A-Za-z_$][\w$]*(?=\s*\()|\b[A-Za-z_$][\w$]*\b|\b\d+(?:\.\d+)?\b|[{}()[\].,;:+\-*/%=<>!&|?]+)/g

function highlightCode(code: string, language?: string): ReactNode[] {
  if (!code) return []

  const normalizedLanguage = normalizeLanguage(language)
  const nodes: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  TOKEN_PATTERN.lastIndex = 0
  while ((match = TOKEN_PATTERN.exec(code)) !== null) {
    const token = match[0]
    if (match.index > lastIndex) {
      nodes.push(code.slice(lastIndex, match.index))
    }
    nodes.push(
      <span key={`${match.index}-${token}`} className={getTokenClass(token, normalizedLanguage)}>
        {token}
      </span>,
    )
    lastIndex = match.index + token.length
  }

  if (lastIndex < code.length) {
    nodes.push(code.slice(lastIndex))
  }

  return nodes
}

function normalizeLanguage(language?: string) {
  if (!language) return undefined
  const aliases: Record<string, string> = {
    shell: 'bash',
    sh: 'bash',
    zsh: 'bash',
    javascript: 'js',
    typescript: 'ts',
    py: 'python',
    kt: 'kotlin',
    yml: 'yaml',
  }
  return aliases[language] ?? language
}

function getTokenClass(token: string, language?: string) {
  if (
    token.startsWith('//') ||
    token.startsWith('/*') ||
    token.startsWith('<!--') ||
    (token.startsWith('#') && language !== 'css')
  ) {
    return '[color:var(--syntax-muted)]'
  }

  if (
    (token.startsWith('"') && token.endsWith('"')) ||
    (token.startsWith("'") && token.endsWith("'")) ||
    (token.startsWith('`') && token.endsWith('`'))
  ) {
    return '[color:var(--syntax-string)]'
  }

  if (token.startsWith('<')) {
    return '[color:var(--syntax-keyword)]'
  }

  if (/^\d/.test(token)) {
    return '[color:var(--syntax-number)]'
  }

  if (KEYWORDS.has(token)) {
    return 'font-semibold [color:var(--syntax-keyword)]'
  }

  if (/^[A-Za-z_$][\w$]*$/.test(token)) {
    return '[color:var(--syntax-function)]'
  }

  return '[color:var(--syntax-operator)]'
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
