import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { SkillCatalogDetail } from '@/apis/agents'

export function AgentSkillDetailDialog({
  detail,
  loading,
  onOpenChange,
  open,
}: {
  detail: SkillCatalogDetail | null
  loading: boolean
  onOpenChange: (open: boolean) => void
  open: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[82vh] max-w-3xl overflow-hidden p-0">
        <DialogHeader className="border-border border-b px-5 py-4">
          <DialogTitle>{detail?.displayName ?? '스킬 상세'}</DialogTitle>
          <DialogDescription>{detail?.description ?? '스킬 정보를 확인합니다.'}</DialogDescription>
        </DialogHeader>
        <div className="max-h-[64vh] overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="text-muted-foreground flex items-center gap-2 py-10 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              상세 조회 중
            </div>
          ) : (
            <div className="space-y-4">
              <div className="border-border grid gap-2 border-y py-3 text-sm sm:grid-cols-2">
                <AgentSkillMeta label="키" value={detail?.name ?? '-'} />
                <AgentSkillMeta label="상태" value={detail?.enabled ? '사용 중' : '미사용'} />
                <AgentSkillMeta label="타입" value={detail?.sourceType ?? '-'} />
                <AgentSkillMeta label="경로" value={detail?.sourcePath ?? '-'} />
              </div>
              {detail?.files?.length ? (
                <div className="border-border rounded-md border p-3">
                  <div className="text-muted-foreground mb-2 text-[11px] tracking-[0.16em] uppercase">
                    파일
                  </div>
                  <div className="flex max-h-24 flex-wrap gap-1.5 overflow-y-auto">
                    {detail.files.map((file) => (
                      <span
                        key={file}
                        className="bg-muted/60 rounded px-2 py-1 font-mono text-[11px]"
                      >
                        {file}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              <pre className="bg-muted/30 border-border max-h-[44vh] overflow-auto rounded-md border p-4 text-xs leading-5 whitespace-pre-wrap">
                <code>{detail?.body || '내용이 없습니다.'}</code>
              </pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function AgentSkillMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-muted-foreground text-[11px] tracking-[0.16em] uppercase">{label}</div>
      <div className="mt-1 truncate font-mono text-xs" title={value}>
        {value}
      </div>
    </div>
  )
}
