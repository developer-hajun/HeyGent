import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'

export function NotionCallbackPage() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const success = params.get('success')
    const error = params.get('error')

    if (success === 'true') {
      window.opener?.postMessage({ type: 'NOTION_CONNECTED' }, '*')
    } else {
      window.opener?.postMessage({ type: 'NOTION_CONNECT_FAILED', error }, '*')
    }

    window.close()
  }, [])

  return (
    <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-[#f2f3f8] dark:bg-[#0f1117]">
      <Loader2 className="text-primary h-8 w-8 animate-spin" />
      <p className="text-muted-foreground text-sm">Notion 연결 중...</p>
    </div>
  )
}
