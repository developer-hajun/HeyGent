import { useState, useRef } from 'react'
import { X, Bot, Sparkles, SlidersHorizontal, Camera, ChevronLeft } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './ui/dialog'

export interface CustomAgentConfig {
  agentName: string
  persona: string
  callName: string
  profileImage: string | null
}

interface NewSessionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (config?: CustomAgentConfig) => void
}

type ModalView = 'select' | 'customize'

export function NewSessionModal({ open, onOpenChange, onConfirm }: NewSessionModalProps) {
  const [view, setView] = useState<ModalView>('select')
  const [agentName, setAgentName] = useState('')
  const [persona, setPersona] = useState('')
  const [callName, setCallName] = useState('')
  const [profileImage, setProfileImage] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleClose = () => {
    onOpenChange(false)
    // 닫을 때 상태 초기화 (애니메이션 후)
    setTimeout(() => {
      setView('select')
      setAgentName('')
      setPersona('')
      setCallName('')
      setProfileImage(null)
    }, 200)
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const url = URL.createObjectURL(file)
    setProfileImage(url)
  }

  const handleCustomizeConfirm = () => {
    onConfirm({ agentName, persona, callName, profileImage })
    setTimeout(() => {
      setView('select')
      setAgentName('')
      setPersona('')
      setCallName('')
      setProfileImage(null)
    }, 200)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        className="w-[480px] gap-0 overflow-hidden p-0 [&>button]:hidden"
        aria-describedby="new-session-description"
      >
        <DialogTitle className="sr-only">새 세션 시작</DialogTitle>
        <DialogDescription id="new-session-description" className="sr-only">
          세션 유형을 선택하거나 에이전트를 커스터마이징합니다
        </DialogDescription>

        <AnimatePresence mode="wait">
          {view === 'select' ? (
            <motion.div
              key="select"
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.18 }}
            >
              {/* Header */}
              <div className="border-border flex items-center justify-between border-b px-6 py-4">
                <div>
                  <h2 className="text-foreground text-base font-semibold">새 세션 시작</h2>
                  <p className="text-muted-foreground mt-0.5 text-xs">세션 유형을 선택하세요</p>
                </div>
                <button
                  onClick={handleClose}
                  className="text-muted-foreground hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Options */}
              <div className="space-y-3 p-6">
                {/* 기본 제공 에이전트 */}
                <button
                  onClick={() => onConfirm()}
                  className="border-border hover:border-primary/40 hover:bg-primary/3 group flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-all duration-150"
                >
                  <div className="bg-primary/10 group-hover:bg-primary/15 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl transition-colors">
                    <Bot className="text-primary h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-foreground text-sm font-semibold">기본 제공 에이전트</p>
                    <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
                      미리 설정된 전문 에이전트를 바로 사용합니다
                    </p>
                  </div>
                </button>

                {/* 에이전트 커스터마이징 */}
                <button
                  onClick={() => setView('customize')}
                  className="border-border group flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-all duration-150 hover:border-violet-300 hover:bg-violet-50/50"
                >
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-violet-100 transition-colors group-hover:bg-violet-200/70">
                    <SlidersHorizontal className="h-5 w-5 text-violet-600" />
                  </div>
                  <div>
                    <p className="text-foreground text-sm font-semibold">에이전트 커스터마이징</p>
                    <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
                      새 대화 시작 전에 표시용 이름과 페르소나를 입력합니다
                    </p>
                  </div>
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="customize"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={{ duration: 0.18 }}
            >
              {/* Header */}
              <div className="border-border flex items-center gap-3 border-b px-6 py-4">
                <button
                  onClick={() => setView('select')}
                  className="text-muted-foreground hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <div className="flex-1">
                  <h2 className="text-foreground text-base font-semibold">에이전트 커스터마이징</h2>
                  <p className="text-muted-foreground mt-0.5 text-xs">
                    새 대화에 사용할 표시용 설정을 입력합니다
                  </p>
                </div>
                <button
                  onClick={handleClose}
                  className="text-muted-foreground hover:text-foreground hover:bg-muted flex h-7 w-7 items-center justify-center rounded-md transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Form */}
              <div className="space-y-5 px-6 py-5">
                {/* Profile Image */}
                <div className="flex flex-col items-center gap-2">
                  <div className="relative">
                    <div className="bg-muted border-border flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border-2">
                      {profileImage ? (
                        <img
                          src={profileImage}
                          alt="프로필"
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <Bot className="text-muted-foreground h-9 w-9" />
                      )}
                    </div>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="bg-primary absolute right-0 bottom-0 flex h-6 w-6 items-center justify-center rounded-full text-white shadow-sm transition-opacity hover:opacity-90"
                    >
                      <Camera className="h-3 w-3" />
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleImageChange}
                    />
                  </div>
                  <p className="text-muted-foreground text-xs">프로필 이미지</p>
                </div>

                {/* Agent Name */}
                <div>
                  <label className="text-foreground mb-1.5 block text-xs font-medium">
                    에이전트 이름
                  </label>
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    placeholder="예: 지우, 알파, 어시스턴트"
                    className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 w-full rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                  />
                </div>

                {/* Persona */}
                <div>
                  <label className="text-foreground mb-1.5 block text-xs font-medium">
                    페르소나
                  </label>
                  <textarea
                    value={persona}
                    onChange={(e) => setPersona(e.target.value)}
                    placeholder="예: 차분하고 논리적인 성격으로, 항상 데이터에 근거해 조언합니다."
                    rows={3}
                    className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 w-full resize-none rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                  />
                </div>

                {/* Call Name */}
                <div>
                  <label className="text-foreground mb-1.5 block text-xs font-medium">
                    어떻게 불러드릴까요?
                  </label>
                  <input
                    type="text"
                    value={callName}
                    onChange={(e) => setCallName(e.target.value)}
                    placeholder="예: 민수님, 팀장님, 이름"
                    className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 w-full rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
                  />
                </div>
              </div>

              {/* Footer */}
              <div className="border-border flex gap-2 border-t px-6 py-4">
                <button
                  onClick={() => setView('select')}
                  className="bg-muted text-foreground hover:bg-muted/80 flex-1 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                >
                  이전
                </button>
                <button
                  onClick={handleCustomizeConfirm}
                  disabled={!agentName.trim()}
                  className="bg-primary hover:bg-primary/90 flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-40"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  설정 완료
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  )
}
