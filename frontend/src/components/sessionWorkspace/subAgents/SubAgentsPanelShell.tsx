import type { ReactNode } from 'react'

export function SubAgentsPanelShell({
  children,
  description,
  hideHeader = false,
  width = 'narrow',
  title,
}: {
  children: ReactNode
  description: string
  hideHeader?: boolean
  width?: 'narrow' | 'wide'
  title: string
}) {
  return (
    <main className="bg-background min-w-0 flex-1 overflow-auto p-4 outline-none md:p-6">
      <div className={`w-full space-y-6 ${width === 'narrow' ? 'mx-auto max-w-2xl' : ''}`}>
        {!hideHeader && (
          <div>
            <h1 className="text-lg font-semibold">{title}</h1>
            <p className="text-muted-foreground mt-1 text-sm">{description}</p>
          </div>
        )}
        {children}
      </div>
    </main>
  )
}
