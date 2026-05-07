import { useState } from 'react'
import { ArrowLeft, Bot, Code2, Cpu, Gem, Network, Rocket, Sparkles, Terminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { cn } from '@/components/ui/utils'
import { SUB_AGENT_ADAPTER_OPTIONS, type SubAgentAdapterType } from './subAgentConfigOptions'

const ADAPTER_ICONS: Record<SubAgentAdapterType, typeof Bot> = {
  claude_local: Bot,
  codex_local: Terminal,
  cursor: Cpu,
  gemini_local: Sparkles,
  hermes_local: Network,
  openclaw_gateway: Rocket,
  opencode_local: Code2,
  pi_local: Gem,
}

export function SubAgentCreateDialog({
  onAskCeo,
  onOpenChange,
  onPickAdapter,
  open,
}: {
  onAskCeo: () => void
  onOpenChange: (open: boolean) => void
  onPickAdapter: (adapterType: SubAgentAdapterType) => void
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
                  조직 구조와 권한을 아는 CEO에게 에이전트 생성을 맡기는 것을 권장합니다.
                </p>
              </div>

              <Button className="w-full" size="lg" onClick={onAskCeo}>
                <Bot className="mr-2 h-4 w-4" />
                CEO에게 새 에이전트 생성 요청
              </Button>

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
                  const comingSoon = 'comingSoon' in option && option.comingSoon
                  const recommended = 'recommended' in option && option.recommended
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
