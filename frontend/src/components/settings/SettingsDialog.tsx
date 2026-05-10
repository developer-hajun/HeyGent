import { useState, useEffect, useRef } from 'react'
import {
  Zap,
  Database,
  Palette,
  Key,
  MessageSquare,
  ChevronDown,
  Check,
  SlidersHorizontal,
  Eye,
  EyeOff,
  Search,
  Globe,
  Loader2,
  CheckCircle2,
} from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { motion, AnimatePresence } from 'motion/react'
import { useChatStore } from '@/store/useChatStore'
import { getOpenAiModels, type OpenAiModelsResponse } from '@/apis/openaiModels'
import { saveOpenAiApiKey, deleteOpenAiApiKey, type ProviderName } from '@/apis/openaiApiKey'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId?: string
  initialTab?: SettingsTab
}

type SettingsTab =
  | 'general'
  | 'skills'
  | 'models'
  | 'personalization'
  | 'apiKeys'
  | 'channels'
  | 'external'

export function SettingsDialog({ open, onOpenChange, sessionId, initialTab }: SettingsDialogProps) {
  const [prevOpen, setPrevOpen] = useState(open)
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab ?? 'general')

  if (prevOpen !== open) {
    setPrevOpen(open)
    if (open && initialTab) {
      setActiveTab(initialTab)
    }
  }

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen)
  }

  const tabs = [
    { id: 'general' as const, label: '일반', icon: SlidersHorizontal },
    { id: 'skills' as const, label: '스킬 목록', icon: Zap },
    { id: 'models' as const, label: '모델', icon: Database },
    { id: 'personalization' as const, label: '개인 맞춤 설정', icon: Palette },
    { id: 'apiKeys' as const, label: 'API 키', icon: Key },
    { id: 'channels' as const, label: '채널 연결', icon: MessageSquare },
    { id: 'external' as const, label: '외부 서비스', icon: Globe },
  ]

  return (
    <Dialog open={open} onOpenChange={handleOpenChange} key={`${String(open)}-${initialTab ?? ''}`}>
      <DialogContent
        className="flex h-[85vh] w-[min(90vw,760px)] max-w-none gap-0 overflow-hidden p-0"
        aria-describedby="settings-description"
      >
        <DialogTitle className="sr-only">설정</DialogTitle>
        <DialogDescription id="settings-description" className="sr-only">
          애플리케이션 설정을 관리합니다
        </DialogDescription>

        <div className="flex h-full min-w-0 flex-1 overflow-hidden">
          {/* Left Sidebar */}
          <div className="border-border bg-muted/30 flex w-52 shrink-0 flex-col border-r p-4">
            <div className="mb-6">
              <h2 className="text-foreground text-lg font-semibold">설정</h2>
            </div>
            <div className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                    activeTab === tab.id
                      ? 'text-foreground bg-white shadow-sm'
                      : 'text-muted-foreground hover:bg-muted'
                  }`}
                >
                  <tab.icon className="h-4 w-4 shrink-0" />
                  <span className="text-sm font-medium">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Right Content */}
          <div className="relative min-h-0 flex-1 overflow-y-auto p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
              >
                {activeTab === 'general' && <GeneralContent />}
                {activeTab === 'skills' && <SkillsContent />}
                {activeTab === 'models' && <ModelsContent sessionId={sessionId} />}
                {activeTab === 'personalization' && <PersonalizationContent />}
                {activeTab === 'apiKeys' && <ApiKeysContent />}
                {activeTab === 'channels' && <ChannelsContent />}
                {activeTab === 'external' && <ExternalServicesContent />}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// General Content
// ────────────────────────────────────────────────────────────────────────────
function GeneralContent() {
  const [settings, setSettings] = useState({
    language: '한국어',
    theme: '시스템 설정',
    notifications: true,
    soundEffects: true,
  })

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">일반</h3>
        <p className="text-muted-foreground text-sm">애플리케이션의 기본 설정을 관리합니다</p>
      </div>

      <div className="space-y-3">
        {/* Language */}
        <div className="border-border rounded-xl border p-4">
          <div className="mb-1 flex items-start justify-between">
            <div className="flex-1">
              <h4 className="text-foreground mb-1 text-sm font-medium">언어</h4>
              <p className="text-muted-foreground text-xs">애플리케이션 표시 언어를 선택합니다</p>
            </div>
          </div>

          <Popover>
            <PopoverTrigger asChild>
              <button className="border-border hover:bg-muted/30 mt-3 flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-colors">
                <span className="text-foreground text-sm">{settings.language}</span>
                <ChevronDown className="text-muted-foreground h-4 w-4" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-2" align="start">
              <div className="space-y-1">
                {['한국어', 'English', '日本語', '中文'].map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setSettings({ ...settings, language: lang })}
                    className="hover:bg-muted flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left transition-colors"
                  >
                    <span className="text-foreground text-sm font-medium">{lang}</span>
                    {settings.language === lang && <Check className="text-primary h-4 w-4" />}
                  </button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Theme */}
        <div className="border-border rounded-xl border p-4">
          <div className="mb-1 flex items-start justify-between">
            <div className="flex-1">
              <h4 className="text-foreground mb-1 text-sm font-medium">테마</h4>
              <p className="text-muted-foreground text-xs">화면 테마를 선택합니다</p>
            </div>
          </div>

          <Popover>
            <PopoverTrigger asChild>
              <button className="border-border hover:bg-muted/30 mt-3 flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-colors">
                <span className="text-foreground text-sm">{settings.theme}</span>
                <ChevronDown className="text-muted-foreground h-4 w-4" />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80 p-2" align="start">
              <div className="space-y-1">
                {['시스템 설정', '라이트 모드', '다크 모드'].map((theme) => (
                  <button
                    key={theme}
                    onClick={() => setSettings({ ...settings, theme })}
                    className="hover:bg-muted flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left transition-colors"
                  >
                    <span className="text-foreground text-sm font-medium">{theme}</span>
                    {settings.theme === theme && <Check className="text-primary h-4 w-4" />}
                  </button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Notifications */}
        <div className="bg-muted/30 border-border flex items-start justify-between rounded-xl border p-4">
          <div className="flex-1 pr-4">
            <h4 className="text-foreground mb-1 text-sm font-medium">알림</h4>
            <p className="text-muted-foreground text-xs">데스크톱 알림을 활성화합니다</p>
          </div>
          <Switch
            checked={settings.notifications}
            onCheckedChange={(checked) => setSettings({ ...settings, notifications: checked })}
          />
        </div>

        {/* Sound Effects */}
        <div className="bg-muted/30 border-border flex items-start justify-between rounded-xl border p-4">
          <div className="flex-1 pr-4">
            <h4 className="text-foreground mb-1 text-sm font-medium">효과음</h4>
            <p className="text-muted-foreground text-xs">알림 및 상호작용 시 효과음을 재생합니다</p>
          </div>
          <Switch
            checked={settings.soundEffects}
            onCheckedChange={(checked) => setSettings({ ...settings, soundEffects: checked })}
          />
        </div>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Skills Content
// ────────────────────────────────────────────────────────────────────────────
function SkillsContent() {
  const [skills, setSkills] = useState([
    {
      id: 'github-pr',
      name: '깃허브 PR 리뷰',
      enabled: true,
      description: 'Pull Request를 자동으로 분석하고 리뷰합니다',
    },
    {
      id: 'reminder',
      name: '리마인드 생성',
      enabled: true,
      description: '일정과 알림을 자동으로 생성하고 관리합니다',
    },
    { id: 'diet', name: '식단 추천', enabled: true, description: '개인 맞춤 식단을 추천합니다' },
    {
      id: 'health',
      name: '헬스 커넥트 조회',
      enabled: false,
      description: '건강 데이터를 조회하고 분석합니다',
    },
    {
      id: 'iot',
      name: 'IoT 알림 전송',
      enabled: true,
      description: 'IoT 기기로 알림을 전송합니다',
    },
  ])
  const [searchQuery, setSearchQuery] = useState('')

  const toggleSkill = (id: string) => {
    setSkills((prev) =>
      prev.map((skill) => (skill.id === id ? { ...skill, enabled: !skill.enabled } : skill)),
    )
  }

  const filteredSkills = skills.filter(
    (skill) =>
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">스킬 목록</h3>
        <p className="text-muted-foreground text-sm">Heygent가 사용할 수 있는 스킬을 관리합니다</p>
      </div>

      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="스킬 검색..."
          className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 w-full rounded-lg border bg-white py-2 pr-3 pl-9 text-sm focus:ring-2 focus:outline-none"
        />
      </div>

      <div className="space-y-3">
        {filteredSkills.map((skill) => (
          <div
            key={skill.id}
            className="bg-muted/30 border-border hover:bg-muted/50 flex items-start justify-between rounded-xl border p-4 transition-colors"
          >
            <div className="flex-1 pr-4">
              <h4 className="text-foreground mb-1 text-sm font-medium">{skill.name}</h4>
              <p className="text-muted-foreground text-xs">{skill.description}</p>
            </div>
            <Switch checked={skill.enabled} onCheckedChange={() => toggleSkill(skill.id)} />
          </div>
        ))}
        {filteredSkills.length === 0 && (
          <p className="text-muted-foreground py-8 text-center text-sm">검색 결과가 없습니다</p>
        )}
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Models Content
// ────────────────────────────────────────────────────────────────────────────
function ModelsContent({ sessionId }: { sessionId?: string }) {
  const updateSessionSettings = useChatStore((state) => state.updateSessionSettings)
  const [modelData, setModelData] = useState<OpenAiModelsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    getOpenAiModels()
      .then((data) => {
        setModelData(data)
        setSelectedModel(data.defaultModel)
      })
      .catch(() => setError('모델 목록을 불러오는데 실패했습니다.'))
      .finally(() => setLoading(false))
  }, [])

  const handleSelectModel = async (modelId: string) => {
    if (sessionId === undefined) {
      setSaveError('세션을 연 뒤 모델을 저장할 수 있습니다.')
      return
    }
    setSelectedModel(modelId)
    setSaveError(null)
    try {
      await updateSessionSettings({ sessionId, settingsPatch: { model: modelId } })
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '모델 설정 저장에 실패했습니다.')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">모델</h3>
        <p className="text-muted-foreground text-sm">
          사용 가능한 AI 모델 목록을 확인하고 현재 대화의 모델을 선택합니다
        </p>
      </div>

      {loading && (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          모델 목록을 불러오는 중입니다.
        </div>
      )}

      {error && (
        <div className="border-border bg-muted/30 text-muted-foreground rounded-xl border p-4 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && modelData && (
        <div className="space-y-5">
          {modelData.providers.map((provider) => (
            <div key={provider.providerName}>
              <h4 className="text-foreground mb-2 text-sm font-semibold">{provider.displayName}</h4>
              <div className="space-y-2">
                {provider.models.map((modelId) => (
                  <button
                    key={modelId}
                    type="button"
                    onClick={() => void handleSelectModel(modelId)}
                    className={`border-border flex w-full items-start justify-between rounded-xl border p-4 text-left transition-colors ${
                      selectedModel === modelId ? 'bg-primary/5 border-primary/30' : 'bg-muted/30'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <h5 className="text-foreground truncate text-sm font-medium">{modelId}</h5>
                      <p className="text-muted-foreground mt-1 text-xs">{provider.displayName}</p>
                    </div>
                    {selectedModel === modelId && (
                      <Check className="text-primary h-4 w-4 shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {saveError && <p className="text-destructive text-sm">{saveError}</p>}
      {sessionId === undefined && (
        <p className="text-muted-foreground text-xs">
          대화별 모델 저장은 채팅 화면에서 설정을 열었을 때만 적용됩니다.
        </p>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Personalization Content
// ────────────────────────────────────────────────────────────────────────────
function PersonalizationContent() {
  const [settings, setSettings] = useState({
    nickname: 'Heygent',
    tone: '기본값',
    emoji: true,
    formality: '보통',
    language: '자동 탐지',
  })

  const sections = [
    {
      id: 'tone',
      title: '기본 스타일 및 말투',
      description:
        'ChatGPT가 응답하는 스타일과 말투를 지정합니다. ChatGPT의 성능에는 영향을 주지 않습니다.',
      value: settings.tone,
      options: [
        { value: '기본값', label: '기본값', description: '기본 스타일과 말투' },
        { value: '전문적인', label: '전문적인', description: '정제되어 있고 전문적임' },
        { value: '친근한', label: '친근한', description: '따뜻하고 수다스러움' },
        { value: '솔직함', label: '솔직함', description: '직설적이면서도 격려적' },
        { value: '독특함', label: '독특함', description: '유쾌하고 상상력이 풍부함' },
        { value: '냉소적', label: '냉소적', description: '비꼬면서 비판적임' },
      ],
    },

    {
      id: 'language',
      title: '언어',
      description: '응답 언어를 선택합니다',
      value: settings.language,
      options: [
        { value: '자동 탐지', label: '자동 탐지', description: '' },
        { value: '한국어', label: '한국어', description: '' },
        { value: 'English', label: 'English', description: '' },
        { value: '日本語', label: '日本語', description: '' },
      ],
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">개인 맞춤 설정</h3>
        <p className="text-muted-foreground text-sm">Heygent의 스타일과 말투를 개인화합니다</p>
      </div>

      <div className="space-y-3">
        {/* Nickname */}
        <div className="border-border rounded-xl border p-4">
          <div className="mb-1 flex items-start justify-between">
            <div className="flex-1">
              <h4 className="text-foreground mb-1 text-sm font-medium">음성 호출 이름</h4>
              <p className="text-muted-foreground text-xs">
                음성으로 AI를 호출할 때 사용할 이름을 설정합니다 (예: "헤이전트", "자비스")
              </p>
            </div>
          </div>

          <input
            type="text"
            value={settings.nickname}
            onChange={(e) => setSettings({ ...settings, nickname: e.target.value })}
            placeholder="음성 호출 이름을 입력하세요"
            className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 mt-3 w-full rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
          />
          <p className="text-muted-foreground mt-2 text-xs">예시: "안녕, {settings.nickname}"</p>
        </div>

        {sections.map((section) => (
          <div key={section.id} className="border-border rounded-xl border p-4">
            <div className="mb-1 flex items-start justify-between">
              <div className="flex-1">
                <h4 className="text-foreground mb-1 text-sm font-medium">{section.title}</h4>
                <p className="text-muted-foreground text-xs">{section.description}</p>
              </div>
            </div>

            <Popover>
              <PopoverTrigger asChild>
                <button className="border-border hover:bg-muted/30 mt-3 flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-colors">
                  <span className="text-foreground text-sm">{section.value}</span>
                  <ChevronDown className="text-muted-foreground h-4 w-4" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-80 p-2" align="start">
                <div className="space-y-1">
                  {section.options.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setSettings({ ...settings, [section.id]: option.value })
                      }}
                      className="hover:bg-muted flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors"
                    >
                      <div className="flex-1">
                        <div className="mb-0.5 flex items-center gap-2">
                          <span className="text-foreground text-sm font-medium">
                            {option.label}
                          </span>
                          {settings[section.id as keyof typeof settings] === option.value && (
                            <Check className="text-primary h-4 w-4" />
                          )}
                        </div>
                        {option.description && (
                          <p className="text-muted-foreground text-xs">{option.description}</p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </PopoverContent>
            </Popover>
          </div>
        ))}

        {/* Emoji Toggle */}
        <div className="bg-muted/30 border-border flex items-start justify-between rounded-xl border p-4">
          <div className="flex-1 pr-4">
            <h4 className="text-foreground mb-1 text-sm font-medium">이모지 사용</h4>
            <p className="text-muted-foreground text-xs">
              Heygent는 메뉴로 일반 지식을 활용해 빠르고 길이 있는 답변을 제공합니다. 이는 개인
              맞춤형이 아니며 메모리를 사용하지 않습니다.
            </p>
          </div>
          <Switch
            checked={settings.emoji}
            onCheckedChange={(checked) => setSettings({ ...settings, emoji: checked })}
          />
        </div>
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// API Keys Content
// ────────────────────────────────────────────────────────────────────────────
const API_KEY_GUIDES = {
  openai_api_key: {
    placeholder: 'sk-proj-...',
    steps: [
      {
        before: '',
        linkLabel: 'OpenAI Platform',
        href: 'https://platform.openai.com',
        after: '에 접속합니다.',
      },
      { text: '로그인 후 우측 상단 메뉴에서 API Keys를 선택합니다.' },
      { text: 'Create new secret key 버튼을 눌러 키를 생성합니다.' },
      { text: '생성된 키는 한 번만 표시됩니다. 바로 복사해 안전한 곳에 저장하세요.' },
    ],
  },
  gemini_api_key: {
    placeholder: 'AIza...',
    steps: [
      {
        before: '',
        linkLabel: 'Google AI Studio',
        href: 'https://aistudio.google.com/apikey',
        after: '에 접속합니다.',
      },
      { text: 'Google 계정으로 로그인합니다.' },
      { text: 'Create API key 버튼을 눌러 키를 생성합니다.' },
      { text: '생성된 키를 복사해 안전한 곳에 저장하세요.' },
    ],
  },
  claude_api_key: {
    placeholder: 'sk-ant-...',
    steps: [
      {
        before: '',
        linkLabel: 'Anthropic Console',
        href: 'https://console.anthropic.com',
        after: '에 접속합니다.',
      },
      { text: '로그인 후 좌측 메뉴에서 API Keys를 선택합니다.' },
      { text: 'Create Key 버튼을 눌러 키를 생성합니다.' },
      { text: '생성된 키는 한 번만 표시됩니다. 바로 복사해 안전한 곳에 저장하세요.' },
    ],
  },
} as const

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

function ApiKeysContent() {
  const [apiKeys, setApiKeys] = useState([
    { id: 'openai_api_key' as const, name: 'OpenAI API', value: '', visible: false },
    { id: 'gemini_api_key' as const, name: 'Gemini API', value: '', visible: false },
    { id: 'claude_api_key' as const, name: 'Claude API', value: '', visible: false },
  ])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [saveStatuses, setSaveStatuses] = useState<Record<string, SaveStatus>>({})
  const [saveErrors, setSaveErrors] = useState<Record<string, string | null>>({})
  const [deleteStatuses, setDeleteStatuses] = useState<Record<string, SaveStatus>>({})

  const toggleVisibility = (id: string) => {
    setApiKeys((prev) => prev.map((k) => (k.id === id ? { ...k, visible: !k.visible } : k)))
  }

  const handleDelete = async (id: ProviderName) => {
    setDeleteStatuses((prev) => ({ ...prev, [id]: 'saving' }))
    try {
      await deleteOpenAiApiKey(id)
      setApiKeys((prev) => prev.map((k) => (k.id === id ? { ...k, value: '' } : k)))
      setDeleteStatuses((prev) => ({ ...prev, [id]: 'saved' }))
      setTimeout(() => setDeleteStatuses((prev) => ({ ...prev, [id]: 'idle' })), 2000)
    } catch {
      setDeleteStatuses((prev) => ({ ...prev, [id]: 'error' }))
    }
  }

  const handleSave = async (id: ProviderName) => {
    const key = apiKeys.find((k) => k.id === id)
    if (!key || !key.value.trim()) return
    setSaveStatuses((prev) => ({ ...prev, [id]: 'saving' }))
    setSaveErrors((prev) => ({ ...prev, [id]: null }))
    try {
      await saveOpenAiApiKey(id, { apiKey: key.value.trim() })
      setSaveStatuses((prev) => ({ ...prev, [id]: 'saved' }))
      setTimeout(() => setSaveStatuses((prev) => ({ ...prev, [id]: 'idle' })), 2000)
    } catch (e) {
      setSaveStatuses((prev) => ({ ...prev, [id]: 'error' }))
      setSaveErrors((prev) => ({
        ...prev,
        [id]: e instanceof Error ? e.message : '저장에 실패했습니다.',
      }))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">API 키</h3>
        <p className="text-muted-foreground text-sm">
          외부 서비스 연동을 위한 API 키를 입력해 주세요
        </p>
      </div>

      <div className="space-y-3">
        {apiKeys.map((key) => {
          const guide = API_KEY_GUIDES[key.id]
          return (
            <div key={key.id} className="bg-muted/30 border-border space-y-3 rounded-xl border p-4">
              {/* 레이블 + 버튼 행 */}
              <div className="flex items-center justify-between gap-4">
                <label className="text-foreground shrink-0 text-sm font-medium">{key.name}</label>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setExpandedId(expandedId === key.id ? null : key.id)}
                    className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs whitespace-nowrap transition-colors"
                  >
                    <span>{expandedId === key.id ? '접기' : '발급 방법 보기'}</span>
                    <ChevronDown
                      className={`h-3.5 w-3.5 transition-transform duration-200 ${expandedId === key.id ? 'rotate-180' : ''}`}
                    />
                  </button>
                </div>
              </div>

              {/* 입력창 */}
              <div className="relative">
                <input
                  type={key.visible ? 'text' : 'password'}
                  value={key.value}
                  onChange={(e) =>
                    setApiKeys((prev) =>
                      prev.map((k) => (k.id === key.id ? { ...k, value: e.target.value } : k)),
                    )
                  }
                  placeholder={guide.placeholder}
                  className="border-border text-foreground placeholder:text-muted-foreground focus:ring-ring/20 w-full rounded-lg border bg-transparent py-2 pr-10 pl-3 text-sm focus:ring-2 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => toggleVisibility(key.id)}
                  className="text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2 transition-colors"
                >
                  {key.visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </button>
              </div>

              {/* 저장/삭제 버튼 행 */}
              <div className="flex items-center justify-between gap-2">
                {saveStatuses[key.id] === 'error' && saveErrors[key.id] ? (
                  <p className="text-destructive text-xs">{saveErrors[key.id]}</p>
                ) : saveStatuses[key.id] === 'saved' ? (
                  <p className="flex items-center gap-1 text-xs text-emerald-500">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    저장됐습니다
                  </p>
                ) : deleteStatuses[key.id] === 'saved' ? (
                  <p className="flex items-center gap-1 text-xs text-emerald-500">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    삭제됐습니다
                  </p>
                ) : deleteStatuses[key.id] === 'error' ? (
                  <p className="text-destructive text-xs">삭제에 실패했습니다.</p>
                ) : (
                  <span />
                )}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={deleteStatuses[key.id] === 'saving'}
                    onClick={() => void handleDelete(key.id)}
                    className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-500 transition-colors hover:bg-red-50 disabled:opacity-40 dark:border-red-800 dark:hover:bg-red-950"
                  >
                    {deleteStatuses[key.id] === 'saving' ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {deleteStatuses[key.id] === 'saving' ? '삭제 중...' : '삭제'}
                  </button>
                  <button
                    type="button"
                    disabled={!key.value.trim() || saveStatuses[key.id] === 'saving'}
                    onClick={() => void handleSave(key.id)}
                    className="bg-foreground text-background hover:bg-foreground/85 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40"
                  >
                    {saveStatuses[key.id] === 'saving' ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    {saveStatuses[key.id] === 'saving' ? '저장 중...' : '저장'}
                  </button>
                </div>
              </div>

              {/* 아코디언 발급 안내 */}
              {expandedId === key.id && (
                <div className="border-border/60 space-y-3 border-t pt-3">
                  <ol className="space-y-2">
                    {guide.steps.map((step, i) => (
                      <li key={i} className="flex gap-2.5 text-sm">
                        <span className="text-muted-foreground shrink-0 font-medium">{i + 1}.</span>
                        <span className="text-muted-foreground leading-5">
                          {'href' in step ? (
                            <>
                              {step.before}
                              <a
                                href={step.href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-foreground underline underline-offset-2 transition-opacity hover:opacity-70"
                              >
                                {step.linkLabel}
                              </a>
                              {step.after}
                            </>
                          ) : (
                            step.text
                          )}
                        </span>
                      </li>
                    ))}
                  </ol>
                  <div className="bg-muted space-y-1 rounded-lg px-3 py-2.5">
                    <p className="text-foreground text-xs font-medium">⚠️ 보안 주의사항</p>
                    <ul className="text-muted-foreground space-y-0.5 text-xs leading-5">
                      <li>• API 키는 비밀번호와 같습니다. 절대 타인과 공유하지 마세요.</li>
                      <li>• 키가 노출되었다면 즉시 삭제 후 재발급받으세요.</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Channels Content
// ────────────────────────────────────────────────────────────────────────────
function ChannelsContent() {
  const [channels, setChannels] = useState([
    { id: 'telegram', name: 'Telegram', connected: true, icon: '📱' },
    { id: 'discord', name: 'Discord', connected: false, icon: '💬' },
    { id: 'slack', name: 'Slack', connected: true, icon: '💼' },
    { id: 'whatsapp', name: 'WhatsApp', connected: false, icon: '📞' },
  ])

  const toggleChannel = (id: string) => {
    setChannels((prev) =>
      prev.map((channel) =>
        channel.id === id ? { ...channel, connected: !channel.connected } : channel,
      ),
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">채널 연결</h3>
        <p className="text-muted-foreground text-sm">
          Telegram, Discord, Slack, WhatsApp 등 연결 가능한 채널 목록과 상태를 조회합니다
        </p>
      </div>

      <div className="space-y-3">
        {channels.map((channel) => (
          <div
            key={channel.id}
            className={`rounded-xl border p-4 transition-all ${
              channel.connected ? 'bg-primary/5 border-primary/20' : 'bg-muted/30 border-border'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{channel.icon}</span>
                <div>
                  <h4 className="text-foreground text-sm font-medium">{channel.name}</h4>
                  <span
                    className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${
                      channel.connected ? 'text-emerald-600' : 'text-muted-foreground'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        channel.connected ? 'bg-emerald-500' : 'bg-muted-foreground'
                      }`}
                    />
                    {channel.connected ? '연결됨' : '미연결'}
                  </span>
                </div>
              </div>
              <button
                onClick={() => toggleChannel(channel.id)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  channel.connected
                    ? 'bg-muted text-muted-foreground hover:bg-muted/80'
                    : 'bg-primary hover:bg-primary/90 text-white'
                }`}
              >
                {channel.connected ? '연결 해제' : '연결하기'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// External Services Content
// ────────────────────────────────────────────────────────────────────────────
function ExternalServicesContent() {
  const [notionConnected, setNotionConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 마운트 시 연결 상태 조회
  useEffect(() => {
    import('@/apis/notion').then(({ getNotionStatus }) => {
      getNotionStatus()
        .then((res) => setNotionConnected(res.data.connected))
        .catch(() => {})
    })
  }, [])

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const handleNotionConnect = async () => {
    try {
      setLoading(true)
      // 팝업 차단 방지: 창 먼저 열고 URL 나중에 설정
      const popup = window.open('about:blank', '_blank')
      const { getNotionConnectUrl, getNotionStatus } = await import('@/apis/notion')
      const res = await getNotionConnectUrl()
      if (popup) {
        popup.location.href = res.data.url
      } else {
        window.open(res.data.url, '_blank')
      }

      // OAuth 창 열고 나서 연결 완료될 때까지 폴링
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await getNotionStatus()
          if (statusRes.data.connected) {
            setNotionConnected(true)
            stopPolling()
            setLoading(false)
          }
        } catch {
          stopPolling()
          setLoading(false)
        }
      }, 2000)

      // 2분 후 자동 폴링 중단
      setTimeout(() => {
        stopPolling()
        setLoading(false)
      }, 120000)
    } catch {
      setLoading(false)
    }
  }

  const handleNotionDisconnect = async () => {
    try {
      const { disconnectNotion } = await import('@/apis/notion')
      await disconnectNotion()
      setNotionConnected(false)
    } catch {
      // 에러 무시
    }
  }

  useEffect(() => () => stopPolling(), [])

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">외부 서비스</h3>
        <p className="text-muted-foreground text-sm">외부 서비스를 연결하여 기능을 확장합니다</p>
      </div>

      <div className="space-y-3">
        <div
          className={`rounded-xl border p-4 transition-all ${
            notionConnected ? 'bg-primary/5 border-primary/20' : 'bg-muted/30 border-border'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-black">
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5 fill-white"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z" />
                </svg>
              </div>
              <div>
                <h4 className="text-foreground text-sm font-medium">Notion</h4>
                <span
                  className={`mt-1 inline-flex items-center gap-1 text-xs font-medium ${
                    notionConnected ? 'text-emerald-600' : 'text-muted-foreground'
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      notionConnected ? 'bg-emerald-500' : 'bg-muted-foreground'
                    }`}
                  />
                  {notionConnected ? '연결됨' : '미연결'}
                </span>
              </div>
            </div>
            <button
              onClick={notionConnected ? handleNotionDisconnect : handleNotionConnect}
              disabled={loading}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${
                notionConnected
                  ? 'bg-muted text-muted-foreground hover:bg-muted/80'
                  : 'bg-primary hover:bg-primary/90 text-white'
              }`}
            >
              {loading ? '연결 중...' : notionConnected ? '연결 해제' : '연결하기'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
