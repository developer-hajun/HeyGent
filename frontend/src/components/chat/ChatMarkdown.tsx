import type { ComponentPropsWithoutRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

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
        pre: ({ children }) => (
          <pre className="bg-muted border-border my-3 max-w-full overflow-x-auto rounded-md border px-3 py-2 text-xs leading-5">
            {children}
          </pre>
        ),
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
