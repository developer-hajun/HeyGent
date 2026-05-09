import { useState } from 'react'
import { ArrowLeft, Bot, Terminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { cn } from '@/components/ui/utils'
import { SUB_AGENT_ADAPTER_OPTIONS, type SubAgentAdapterType } from './subAgentConfigOptions'
import { SUB_AGENT_TEMPLATES, type SubAgentTemplateId } from './subAgentTemplates'

const ADAPTER_ICONS: Record<SubAgentAdapterType, typeof Bot> = {
  claude_local: Bot,
  codex_local: Terminal,
}

export function SubAgentCreateDialog({
  onAskCeo,
  onOpenChange,
  onPickAdapter,
  onPickTemplate,
  open,
}: {
  onAskCeo: () => void
  onOpenChange: (open: boolean) => void
  onPickAdapter: (adapterType: SubAgentAdapterType) => void
  onPickTemplate: (templateId: SubAgentTemplateId) => void
  open: boolean
}) {
  const [showAdvancedCards, setShowAdvancedCards] = useState(false)

  const closeDialog = () => {
    setShowAdvancedCards(false)
    onOpenChange(false)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) setShowAdvancedCards(false)
        onOpenChange(nextOpen)
      }}
    >
      <DialogContent showCloseButton={false} className="gap-0 overflow-hidden p-0 sm:max-w-md">
        <DialogTitle className="sr-only">새 에이전트 추가</DialogTitle>
        <DialogDescription className="sr-only">
          CEO에게 생성을 요청하거나 직접 세부 설정으로 새 서브에이전트를 추가합니다.
        </DialogDescription>
        <div className="border-border flex items-center justify-between border-b px-4 py-2.5">
          <span className="text-muted-foreground text-sm">새 에이전트 추가</span>
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

        <div className="space-y-6 p-6">
          {!showAdvancedCards ? (
            <>
              <div className="space-y-3 text-center">
                <div className="bg-accent mx-auto flex h-12 w-12 items-center justify-center rounded-full">
                  <Bot className="text-foreground h-6 w-6" />
                </div>
                <p className="text-muted-foreground text-sm">
                  대화 맥락과 필요한 역할을 잘 아는 CEO에게 에이전트 생성을 맡길 수 있습니다.
                </p>
              </div>

              <Button className="w-full" size="lg" onClick={onAskCeo}>
                <Bot className="mr-2 h-4 w-4" />
                CEO에게 새 에이전트 생성 요청
              </Button>

              <div className="space-y-2">
                <div className="text-muted-foreground text-left text-xs font-medium">
                  기본 제공 에이전트
                </div>
                <div className="grid gap-2">
                  {SUB_AGENT_TEMPLATES.map((template) => {
                    const Icon = template.icon
                    return (
                      <button
                        key={template.id}
                        type="button"
                        className="border-border hover:bg-accent/50 flex items-start gap-3 rounded-md border p-3 text-left transition-colors"
                        onClick={() => onPickTemplate(template.id)}
                      >
                        <span className="bg-muted/70 mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md">
                          <Icon className="h-4 w-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">
                            {template.name}
                          </span>
                          <span className="text-muted-foreground mt-0.5 line-clamp-2 block text-xs leading-5">
                            {template.description}
                          </span>
                        </span>
                      </button>
                    )
                  })}
                </div>
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
                  세부 설정에 사용할 연결 방식을 선택하세요.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {SUB_AGENT_ADAPTER_OPTIONS.map((option) => {
                  const Icon = ADAPTER_ICONS[option.id]
                  const comingSoon = false
                  const recommended = option.recommended
                  return (
                    <button
                      key={option.id}
                      type="button"
                      className={cn(
                        'border-border hover:bg-accent/50 relative flex flex-col items-center gap-1.5 rounded-md border p-3 text-xs transition-colors',
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
                      <span className="text-muted-foreground text-[10px]">
                        {option.description}
                      </span>
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
