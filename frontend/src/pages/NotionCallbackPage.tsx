import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export function NotionCallbackPage() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const status = params.get('status')
    const error = params.get('error')

    if (status === 'success') {
      window.opener?.postMessage({ type: 'NOTION_CONNECTED' }, '*')
    } else {
      window.opener?.postMessage({ type: 'NOTION_CONNECT_FAILED', error }, '*')
    }

    window.close()
  }, [])

  return (
    <div className="bg-background flex h-screen w-full flex-col items-center justify-center gap-4">
      <Loader2 className="text-primary h-8 w-8 animate-spin" />
      <p className="text-muted-foreground text-sm">Notion 연결 중...</p>
    </div>
  )
}
