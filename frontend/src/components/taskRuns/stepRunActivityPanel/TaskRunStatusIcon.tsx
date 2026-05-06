import { CheckCircle2, Clock3, FileText, Loader2, XCircle } from 'lucide-react'
import type { TaskRunStatusTone } from '@/types/taskRuns'

export function TaskRunStatusIcon({ tone }: { tone: TaskRunStatusTone }) {
  if (tone === 'completed')
    return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
  if (tone === 'failed') return <XCircle className="text-destructive mt-0.5 h-4 w-4 shrink-0" />
  if (tone === 'waiting') return <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
  if (tone === 'running') {
    return <Loader2 className="text-primary mt-0.5 h-4 w-4 shrink-0 animate-spin" />
  }
  return <FileText className="text-muted-foreground mt-0.5 h-4 w-4 shrink-0" />
}
