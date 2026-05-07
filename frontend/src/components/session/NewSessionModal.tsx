import { useState } from 'react'
import { X, Bot, Sparkles, SlidersHorizontal, ChevronLeft, ChevronRight } from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import {
  AgentAdapterTypeDropdown,
  AgentInstructionsBundlePanel,
  AgentModelDropdown,
  AgentSectionCard,
} from '@/components/sessionWorkspace/AgentDetailPanels'

export interface CustomAgentConfig {
  agentName: string
  persona: string
  callName: string
  capabilities: string
  profileImage: string | null
  model: string
  delegationPolicy: {
    canDelegate: boolean
    maxWorkerDepth: number
  }
  instructionsEntryFile: string
  instructionsMode: 'managed' | 'external'
  instructionsRootPath: string
  instructionsFiles: Record<string, string>
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
  const [capabilities, setCapabilities] = useState('')
  const [profileImage, setProfileImage] = useState<string>(CEO_IMAGE_OPTIONS[0].src)
  const [instructionsEntryFile, setInstructionsEntryFile] = useState('AGENTS.md')
  const [instructionsMode, setInstructionsMode] = useState<'managed' | 'external'>('managed')
  const [instructionsRootPath, setInstructionsRootPath] = useState('')
  const [instructionsFiles, setInstructionsFiles] = useState<Record<string, string>>({})
  const [model, setModel] = useState('gpt-5.4')
  const [canDelegate, setCanDelegate] = useState(false)
  const [maxWorkerDepth, setMaxWorkerDepth] = useState(0)
  const selectedImageIndex = Math.max(
    0,
    CEO_IMAGE_OPTIONS.findIndex((option) => option.src === profileImage),
  )

  const handleClose = () => {
    onOpenChange(false)
    // 닫을 때 상태 초기화 (애니메이션 후)
    setTimeout(() => {
      setView('select')
      setAgentName('')
      setPersona('')
      setCallName('')
      setCapabilities('')
      setProfileImage(CEO_IMAGE_OPTIONS[0].src)
      setInstructionsEntryFile('AGENTS.md')
      setInstructionsMode('managed')
      setInstructionsRootPath('')
      setInstructionsFiles({})
      setModel('gpt-5.4')
      setCanDelegate(false)
      setMaxWorkerDepth(0)
    }, 200)
  }

  const handleCustomizeConfirm = () => {
    onConfirm({
      agentName,
      persona,
      callName,
      capabilities,
      profileImage,
      model,
      delegationPolicy: { canDelegate, maxWorkerDepth },
      instructionsEntryFile,
      instructionsMode,
      instructionsRootPath,
      instructionsFiles,
    })
    setTimeout(() => {
      setView('select')
      setAgentName('')
      setPersona('')
      setCallName('')
      setCapabilities('')
      setProfileImage(CEO_IMAGE_OPTIONS[0].src)
      setInstructionsEntryFile('AGENTS.md')
      setInstructionsMode('managed')
      setInstructionsRootPath('')
      setInstructionsFiles({})
      setModel('gpt-5.4')
      setCanDelegate(false)
      setMaxWorkerDepth(0)
    }, 200)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        className="max-h-[88vh] w-[860px] max-w-[calc(100vw-24px)] gap-0 overflow-hidden p-0 [&>button]:hidden"
        aria-describedby="new-session-description"
      >
        <DialogTitle className="sr-only">새 대화 시작</DialogTitle>
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
                  <h2 className="text-foreground text-base font-semibold">새 대화 시작</h2>
                  <p className="text-muted-foreground mt-0.5 text-xs">대화 유형을 선택하세요</p>
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

              <div className="max-h-[calc(88vh-137px)] space-y-6 overflow-y-auto px-6 py-5">
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.82fr)]">
                  <div className="space-y-4">
                    <AgentSectionCard title="프로필">
                      <div className="grid gap-4 sm:grid-cols-[14rem_minmax(0,1fr)]">
                        <AgentImageStepper
                          profileImage={profileImage}
                          selectedImageIndex={selectedImageIndex}
                          onProfileImageChange={setProfileImage}
                        />
                        <div className="space-y-3">
                          <Field label="이름">
                            <input
                              type="text"
                              value={agentName}
                              onChange={(event) => setAgentName(event.target.value)}
                              placeholder="에이전트 이름"
                              className={inputClass}
                            />
                          </Field>
                          <Field label="호칭">
                            <input
                              type="text"
                              value={callName}
                              onChange={(event) => setCallName(event.target.value)}
                              placeholder="CEO"
                              className={inputClass}
                            />
                          </Field>
                          <Field label="할 수 있는 일">
                            <textarea
                              value={capabilities}
                              onChange={(event) => setCapabilities(event.target.value)}
                              rows={3}
                              placeholder="이 에이전트가 할 수 있는 일을 적어주세요."
                              className={`${inputClass} resize-y leading-6`}
                            />
                          </Field>
                        </div>
                      </div>
                    </AgentSectionCard>

                    <AgentSectionCard title="실행 환경">
                      <div className="grid gap-3 sm:grid-cols-3">
                        <Field label="기본 환경">
                          <select
                            className={`${inputClass} cursor-not-allowed opacity-70`}
                            disabled
                          >
                            <option>회사 기본값 (로컬)</option>
                          </select>
                        </Field>
                        <Field label="역할">
                          <input
                            className={`${inputClass} opacity-70`}
                            value="CEO"
                            disabled
                            readOnly
                          />
                        </Field>
                        <Field label="상위 에이전트">
                          <input
                            className={`${inputClass} opacity-70`}
                            value="Root"
                            disabled
                            readOnly
                          />
                        </Field>
                      </div>
                    </AgentSectionCard>
                  </div>

                  <div className="space-y-4">
                    <AgentSectionCard title="연결 방식">
                      <Field label="연결 방식">
                        <AgentAdapterTypeDropdown
                          value="gpt"
                          options={[{ value: 'gpt', label: 'OpenAI API' }]}
                          onChange={() => undefined}
                        />
                      </Field>
                    </AgentSectionCard>

                    <AgentSectionCard title="모델과 권한">
                      <Field label="모델">
                        <AgentModelDropdown
                          value={model}
                          options={[{ value: 'gpt-5.4', label: 'gpt-5.4' }]}
                          onChange={setModel}
                          allowDefault
                        />
                      </Field>
                    </AgentSectionCard>

                    <AgentSectionCard title="실행 규칙">
                      <label className="border-border hover:bg-accent/40 flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors">
                        <input
                          type="checkbox"
                          checked={canDelegate}
                          onChange={(event) => {
                            const checked = event.target.checked
                            setCanDelegate(checked)
                            if (!checked) setMaxWorkerDepth(0)
                          }}
                          className="border-border mt-0.5 h-4 w-4 rounded"
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium">필요할 때 실행 허용</span>
                          <span className="text-muted-foreground mt-0.5 block text-xs leading-5">
                            세션 안에서 필요한 작업을 다른 에이전트에게 맡길 수 있습니다.
                          </span>
                        </span>
                      </label>
                      {canDelegate && (
                        <Field label="동시 실행 수">
                          <select
                            className={inputClass}
                            value={maxWorkerDepth}
                            onChange={(event) => setMaxWorkerDepth(Number(event.target.value))}
                          >
                            <option value={0}>0</option>
                            <option value={1}>1</option>
                          </select>
                        </Field>
                      )}
                    </AgentSectionCard>

                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">API 키</h3>
                      <div className="border-border rounded-lg border p-4">
                        <p className="text-muted-foreground text-sm">
                          API 키는 전역 설정의 제공자 연결에서 관리합니다.
                        </p>
                      </div>
                    </div>

                    <div className="text-muted-foreground text-sm">
                      설정 변경 기록은 대화를 만든 뒤 표시됩니다.
                    </div>
                  </div>
                </div>

                <AgentSectionCard title="지침">
                  <AgentInstructionsBundlePanel
                    content={persona}
                    entryFile={instructionsEntryFile}
                    files={instructionsFiles}
                    mode={instructionsMode}
                    rootPath={instructionsRootPath}
                    onContentChange={setPersona}
                    onEntryFileChange={setInstructionsEntryFile}
                    onFilesChange={setInstructionsFiles}
                    onModeChange={setInstructionsMode}
                    onRootPathChange={setInstructionsRootPath}
                  />
                </AgentSectionCard>
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

const inputClass =
  'border-border placeholder:text-muted-foreground/40 focus-visible:ring-ring w-full rounded-md border bg-transparent px-2.5 py-1.5 text-sm outline-none focus-visible:ring-2'

const CEO_IMAGE_OPTIONS = [
  { id: 'desk', label: '책상', src: '/assets/agents/ceo/ceo_desk.png' },
  { id: 'explain', label: '설명', src: '/assets/agents/ceo/ceo_explain.png' },
  { id: 'profile', label: '프로필', src: '/assets/agents/ceo/ceo_profile.png' },
] as const

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-muted-foreground text-xs">{label}</span>
      {children}
    </label>
  )
}

function AgentImageStepper({
  onProfileImageChange,
  profileImage,
  selectedImageIndex,
}: {
  onProfileImageChange: (image: string) => void
  profileImage: string
  selectedImageIndex: number
}) {
  const selectedImage = CEO_IMAGE_OPTIONS[selectedImageIndex]

  return (
    <div
      className="flex min-h-36 w-full min-w-0 items-center justify-center gap-5 rounded-lg"
      aria-label="에이전트 이미지"
    >
      <button
        type="button"
        onClick={() => {
          const nextIndex =
            (selectedImageIndex - 1 + CEO_IMAGE_OPTIONS.length) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="이전 에이전트 이미지"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="bg-accent hover:bg-accent/80 flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-lg transition-colors"
        aria-label={`${selectedImage?.label ?? '메인 에이전트'} 이미지 변경`}
      >
        <img src={profileImage} alt="" className="h-24 w-24 object-contain" draggable={false} />
      </button>
      <button
        type="button"
        onClick={() => {
          const nextIndex = (selectedImageIndex + 1) % CEO_IMAGE_OPTIONS.length
          onProfileImageChange(CEO_IMAGE_OPTIONS[nextIndex].src)
        }}
        className="text-muted-foreground hover:bg-accent/50 hover:text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded transition-colors"
        aria-label="다음 에이전트 이미지"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  )
}
