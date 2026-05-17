import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, ChevronLeft, ChevronRight, Sparkles, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { HelpHint } from '@/components/ui/help-hint'
import { cn } from '@/components/ui/utils'
import type { AgentTemplate } from '@/apis/agents'
import { SUB_AGENT_ADAPTER_OPTIONS, type SubAgentAdapterType } from './subAgentConfigOptions'

const ADAPTER_ICONS: Record<SubAgentAdapterType, LucideIcon> = {
  openai_api_key: Bot,
  gemini_api_key: Sparkles,
}

export function SubAgentCreateDialog({
  onAskCeo,
  onOpenChange,
  onPickAdapter,
  onPickTemplate,
  open,
  templates,
}: {
  onAskCeo: () => void
  onOpenChange: (open: boolean) => void
  onPickAdapter: (adapterType: SubAgentAdapterType) => void
  onPickTemplate: (templateKey: string) => void
  open: boolean
  templates: AgentTemplate[]
}) {
  const [showAdvancedCards, setShowAdvancedCards] = useState(false)
  const [activeTemplateIndex, setActiveTemplateIndex] = useState(0)

  const closeDialog = () => {
    setShowAdvancedCards(false)
    setActiveTemplateIndex(0)
    onOpenChange(false)
  }

  const activeTemplate =
    templates.length > 0
      ? (templates[Math.min(activeTemplateIndex, templates.length - 1)] ?? null)
      : null

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) setShowAdvancedCards(false)
        onOpenChange(nextOpen)
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="w-[min(94vw,42rem)] gap-0 overflow-hidden p-0 sm:max-w-2xl"
      >
        <DialogTitle className="sr-only">새 에이전트 추가</DialogTitle>
        <DialogDescription className="sr-only">
          팀장 에이전트에게 생성을 요청하거나 직접 세부 설정으로 새 서브에이전트를 추가합니다.
        </DialogDescription>
        <div className="border-border flex items-center justify-between border-b px-4 py-2.5">
          <span className="text-muted-foreground inline-flex items-center gap-1.5 text-sm">
            새 에이전트 추가
            <HelpHint label="서브 에이전트 도움말" iconClassName="h-3.5 w-3.5">
              <p className="text-foreground font-medium">서브 에이전트</p>
              <p>
                팀장 에이전트 밑에서 일을 나눠 맡는 <span className="text-foreground">팀원</span>
                이에요.
              </p>
              <p>예) 리서처는 자료 조사, 디자이너는 시안 작업.</p>
            </HelpHint>
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            className="text-muted-foreground"
            onClick={closeDialog}
            aria-label="닫기"
          >
            <span className="text-lg leading-none">&times;</span>
          </Button>
        </div>

        <div className="space-y-6 px-4 py-5">
          {!showAdvancedCards ? (
            <>
              <div className="space-y-3 text-center">
                <div className="bg-accent mx-auto flex h-12 w-12 items-center justify-center rounded-full">
                  <Bot className="text-foreground h-6 w-6" />
                </div>
                <p className="text-muted-foreground text-sm">
                  대화 맥락과 필요한 역할을 잘 아는 팀장 에이전트에게 에이전트 생성을 맡길 수
                  있습니다.
                </p>
              </div>

              <Button className="w-full" size="lg" onClick={onAskCeo}>
                <Bot className="mr-2 h-4 w-4" />
                팀장 에이전트에게 새 에이전트 생성 요청
              </Button>

              <div className="space-y-3">
                <div className="text-muted-foreground text-left text-xs font-medium">
                  기본 제공 에이전트
                </div>
                <TemplateCarousel
                  templates={templates}
                  activeIndex={activeTemplateIndex}
                  onActiveIndexChange={setActiveTemplateIndex}
                />
                {activeTemplate && (
                  <Button
                    className="w-full"
                    size="lg"
                    onClick={() => onPickTemplate(activeTemplate.templateKey)}
                  >
                    에이전트 생성
                  </Button>
                )}
              </div>

              <div className="text-center">
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground text-xs underline underline-offset-2 transition-colors"
                  onClick={() => setShowAdvancedCards(true)}
                >
                  직접 세부 설정하기
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="space-y-2">
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1 text-xs transition-colors"
                  onClick={() => setShowAdvancedCards(false)}
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  뒤로
                </button>
                <p className="text-muted-foreground text-sm">
                  사용할 모델 공급자를 고르고 세부 설정을 시작합니다.
                </p>
              </div>

              <div className="grid gap-2">
                {SUB_AGENT_ADAPTER_OPTIONS.map((option) => {
                  const Icon = ADAPTER_ICONS[option.id]
                  const comingSoon = false
                  const recommended = option.recommended
                  return (
                    <button
                      key={option.id}
                      type="button"
                      className={cn(
                        'border-border hover:bg-accent/50 relative flex items-center justify-center gap-2 rounded-md border p-3 text-xs transition-colors',
                        comingSoon && 'cursor-not-allowed opacity-40',
                      )}
                      disabled={comingSoon}
                      title={comingSoon ? '준비 중' : undefined}
                      onClick={() => {
                        if (comingSoon) return
                        setShowAdvancedCards(false)
                        onPickAdapter(option.id)
                      }}
                    >
                      {recommended && (
                        <span className="absolute -top-1.5 right-1.5 rounded-full bg-green-500 px-1.5 py-0.5 text-[9px] leading-none font-semibold text-white">
                          추천
                        </span>
                      )}
                      <Icon className="h-4 w-4" />
                      <span className="font-medium">{option.label}</span>
                    </button>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function TemplateCarousel({
  templates,
  activeIndex,
  onActiveIndexChange,
}: {
  templates: AgentTemplate[]
  activeIndex: number
  onActiveIndexChange: (index: number) => void
}) {
  const scrollerRef = useRef<HTMLDivElement | null>(null)
  const total = templates.length

  // 스크롤 위치 → 현재 인덱스 추적
  useEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller) return
    const handleScroll = () => {
      const cardWidth = scroller.clientWidth
      if (cardWidth === 0) return
      const next = Math.round(scroller.scrollLeft / cardWidth)
      onActiveIndexChange(next)
    }
    scroller.addEventListener('scroll', handleScroll, { passive: true })
    return () => scroller.removeEventListener('scroll', handleScroll)
  }, [onActiveIndexChange])

  // activeIndex가 외부에서 변경됐을 때 스크롤 위치도 동기화
  useEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller) return
    const target = Math.max(0, Math.min(total - 1, activeIndex))
    const desiredLeft = target * scroller.clientWidth
    if (Math.abs(scroller.scrollLeft - desiredLeft) > 4) {
      scroller.scrollTo({ left: desiredLeft, behavior: 'smooth' })
    }
  }, [activeIndex, total])

  const goToIndex = (index: number) => {
    const next = Math.max(0, Math.min(total - 1, index))
    onActiveIndexChange(next)
  }

  if (total === 0) {
    return (
      <div className="border-border text-muted-foreground rounded-md border px-3 py-6 text-center text-xs">
        사용 가능한 기본 에이전트가 없습니다.
      </div>
    )
  }

  const canPrev = activeIndex > 0
  const canNext = activeIndex < total - 1

  return (
    <div className="w-full min-w-0 space-y-3">
      <div className="relative w-full min-w-0">
        <div
          ref={scrollerRef}
          className="flex w-full min-w-0 snap-x snap-mandatory overflow-x-auto scroll-smooth [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {templates.map((template) => (
            <div
              key={template.templateKey}
              className="min-w-0 shrink-0 grow-0 basis-full snap-start"
            >
              <div className="border-border flex h-32 w-full items-start gap-3 rounded-md border p-3 pr-12 text-left">
                <span className="bg-muted/70 mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md">
                  <Bot className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{template.displayName}</span>
                  <span className="text-muted-foreground mt-0.5 line-clamp-4 block text-xs leading-5">
                    {template.description}
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
        {canPrev && (
          <button
            type="button"
            aria-label="이전 에이전트"
            onClick={() => goToIndex(activeIndex - 1)}
            className="border-border bg-background/95 text-muted-foreground hover:text-foreground hover:bg-accent/50 absolute top-1/2 left-2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border shadow-sm transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
        {canNext && (
          <button
            type="button"
            aria-label="다음 에이전트"
            onClick={() => goToIndex(activeIndex + 1)}
            className="border-border bg-background/95 text-muted-foreground hover:text-foreground hover:bg-accent/50 absolute top-1/2 right-2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border shadow-sm transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>

      {total > 1 && (
        <div className="flex items-center justify-center gap-1.5">
          {templates.map((template, index) => (
            <button
              key={template.templateKey}
              type="button"
              aria-label={`${index + 1}번째 에이전트로 이동`}
              onClick={() => goToIndex(index)}
              className={cn(
                'h-1.5 rounded-full transition-all',
                index === activeIndex
                  ? 'bg-foreground/70 w-4'
                  : 'bg-muted-foreground/30 hover:bg-muted-foreground/50 w-1.5',
              )}
            />
          ))}
        </div>
      )}
    </div>
  )
}
