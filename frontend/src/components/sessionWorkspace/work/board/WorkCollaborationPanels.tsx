import { useCallback, useEffect, useState } from 'react'
import { Check, FileText, MessageSquare, Plus, Trash2, X } from 'lucide-react'
import {
  createWorkInteraction,
  createWorkProduct,
  deleteWorkDocument,
  deleteWorkProduct,
  listWorkDocumentRevisions,
  listWorkDocuments,
  listWorkInteractions,
  listWorkProducts,
  respondWorkInteraction,
  upsertWorkDocument,
} from '@/apis/work'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { WorkDocument, WorkInteraction, WorkProduct } from '@/types/work'
import { formatRelativeTime } from './issueBoardPanelUtils'

export function WorkDocumentsPanel({ workId }: { workId: string }) {
  const [items, setItems] = useState<WorkDocument[]>([])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [revisionCountByKey, setRevisionCountByKey] = useState<Record<string, number>>({})

  const refresh = useCallback(
    () =>
      listWorkDocuments(workId).then((response) => {
        setItems(response.items)
        return response.items
      }),
    [workId],
  )

  useEffect(() => {
    let cancelled = false
    void refresh()
      .then((documents) =>
        Promise.all(
          documents.map((document) =>
            listWorkDocumentRevisions(workId, document.documentKey).then(
              (response) => [document.documentKey, response.totalCount] as const,
            ),
          ),
        ),
      )
      .then((counts) => {
        if (cancelled) return
        setRevisionCountByKey(Object.fromEntries(counts))
      })
      .catch(console.error)
    return () => {
      cancelled = true
    }
  }, [refresh, workId])

  const edit = (document: WorkDocument) => {
    setSelectedKey(document.documentKey)
    setTitle(document.title)
    setBody(document.body)
  }

  const save = () => {
    const nextTitle = title.trim()
    if (!nextTitle) return
    const key = selectedKey ?? `doc-${Date.now()}`
    void upsertWorkDocument(workId, key, { title: nextTitle, body, format: 'markdown' })
      .then(() => refresh())
      .then(() => {
        setSelectedKey(null)
        setTitle('')
        setBody('')
      })
      .catch(console.error)
  }

  const remove = (documentKey: string) => {
    void deleteWorkDocument(workId, documentKey)
      .then(() => refresh())
      .catch(console.error)
  }

  return (
    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="space-y-2">
        {items.length === 0 ? (
          <EmptyBox>문서 없음</EmptyBox>
        ) : (
          items.map((document) => (
            <div key={document.documentId} className="rounded-md border p-3">
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 shrink-0" />
                <button
                  type="button"
                  className="min-w-0 flex-1 truncate text-left text-sm font-medium"
                  onClick={() => edit(document)}
                >
                  {document.title}
                </button>
                <span className="text-muted-foreground shrink-0 text-xs">
                  r{document.revisionNumber} · 이력 {revisionCountByKey[document.documentKey] ?? 1}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => remove(document.documentKey)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
              <p className="text-muted-foreground mt-2 line-clamp-2 text-xs">
                {document.body || '본문 없음'} · 수정{' '}
                {document.updatedAt ? formatRelativeTime(document.updatedAt) : '-'}
              </p>
            </div>
          ))
        )}
      </div>
      <div className="rounded-md border p-3">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="문서 제목"
          className="bg-background h-9 w-full rounded border px-2 text-sm outline-none focus:ring-1"
        />
        <Textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="문서 본문"
          className="mt-2 min-h-36 resize-none"
        />
        <Button type="button" size="sm" className="mt-2 h-8 gap-1.5" onClick={save}>
          <Plus className="h-3.5 w-3.5" />
          {selectedKey ? '저장' : '추가'}
        </Button>
      </div>
    </div>
  )
}

export function WorkProductsPanel({ workId }: { workId: string }) {
  const [items, setItems] = useState<WorkProduct[]>([])
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')

  const refresh = useCallback(
    () => listWorkProducts(workId).then((response) => setItems(response.items)),
    [workId],
  )
  useEffect(() => {
    void refresh().catch(console.error)
  }, [refresh])

  const add = () => {
    const nextTitle = title.trim()
    if (!nextTitle) return
    void createWorkProduct(workId, {
      title: nextTitle,
      summary: summary.trim() || null,
      productType: 'note',
      status: 'draft',
      reviewState: 'none',
    })
      .then(() => refresh())
      .then(() => {
        setTitle('')
        setSummary('')
      })
      .catch(console.error)
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 rounded-md border p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="결과물 제목"
          className="bg-background h-9 rounded border px-2 text-sm outline-none focus:ring-1"
        />
        <input
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          placeholder="요약"
          className="bg-background h-9 rounded border px-2 text-sm outline-none focus:ring-1"
        />
        <Button type="button" size="sm" className="h-9 gap-1.5" onClick={add}>
          <Plus className="h-3.5 w-3.5" />
          추가
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyBox>결과물 없음</EmptyBox>
      ) : (
        items.map((product) => (
          <div key={product.productId} className="rounded-md border p-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{product.title}</span>
              <span className="rounded-full border px-2 py-0.5 text-xs">{product.status}</span>
              <span className="rounded-full border px-2 py-0.5 text-xs">{product.reviewState}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={() =>
                  deleteWorkProduct(product.productId).then(refresh).catch(console.error)
                }
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
            <p className="text-muted-foreground mt-2 text-xs">{product.summary || '요약 없음'}</p>
          </div>
        ))
      )}
    </div>
  )
}

export function WorkInteractionsPanel({ workId }: { workId: string }) {
  const [items, setItems] = useState<WorkInteraction[]>([])
  const [body, setBody] = useState('')

  const refresh = useCallback(
    () => listWorkInteractions(workId).then((response) => setItems(response.items)),
    [workId],
  )
  useEffect(() => {
    void refresh().catch(console.error)
  }, [refresh])

  const addQuestion = () => {
    const nextBody = body.trim()
    if (!nextBody) return
    void createWorkInteraction(workId, {
      kind: 'ask_user_questions',
      title: '사용자 확인 필요',
      body: nextBody,
      continuationPolicy: 'wake_assignee_on_accept',
    })
      .then(refresh)
      .then(() => setBody(''))
      .catch(console.error)
  }

  const update = (interactionId: string, action: 'accept' | 'reject' | 'cancel') => {
    void respondWorkInteraction(interactionId, action).then(refresh).catch(console.error)
  }

  return (
    <div className="space-y-3">
      <div className="rounded-md border p-3">
        <Textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="사용자 확인이 필요한 내용"
          className="min-h-20 resize-none"
        />
        <Button type="button" size="sm" className="mt-2 h-8 gap-1.5" onClick={addQuestion}>
          <MessageSquare className="h-3.5 w-3.5" />
          추가
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyBox>확인 요청 없음</EmptyBox>
      ) : (
        items.map((interaction) => (
          <div key={interaction.interactionId} className="rounded-md border p-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-sm font-medium">
                {interaction.title || interaction.kind}
              </span>
              <span className="rounded-full border px-2 py-0.5 text-xs">{interaction.status}</span>
            </div>
            <p className="text-muted-foreground mt-2 text-xs whitespace-pre-wrap">
              {interaction.body}
            </p>
            {interaction.status === 'pending' && (
              <div className="mt-3 flex gap-1">
                <Button
                  type="button"
                  size="sm"
                  className="h-8 gap-1.5"
                  onClick={() => update(interaction.interactionId, 'accept')}
                >
                  <Check className="h-3.5 w-3.5" />
                  수락
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5"
                  onClick={() => update(interaction.interactionId, 'reject')}
                >
                  <X className="h-3.5 w-3.5" />
                  거절
                </Button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )
}

function EmptyBox({ children }: { children: string }) {
  return <div className="text-muted-foreground rounded-md border p-4 text-sm">{children}</div>
}
