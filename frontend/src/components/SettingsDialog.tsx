import { useState } from 'react'
import {
  Zap,
  Database,
  Palette,
  Key,
  MessageSquare,
  ChevronDown,
  Check,
  SlidersHorizontal,
} from 'lucide-react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './ui/dialog'
import { Switch } from './ui/switch'
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover'
import { motion, AnimatePresence } from 'motion/react'

interface SettingsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type SettingsTab = 'general' | 'skills' | 'models' | 'personalization' | 'apiKeys' | 'channels'

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general')

  const tabs = [
    { id: 'general' as const, label: '일반', icon: SlidersHorizontal },
    { id: 'skills' as const, label: '스킬 목록', icon: Zap },
    { id: 'models' as const, label: '모델', icon: Database },
    { id: 'personalization' as const, label: '개인 맞춤 설정', icon: Palette },
    { id: 'apiKeys' as const, label: 'API 키', icon: Key },
    { id: 'channels' as const, label: '채널 연결', icon: MessageSquare },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="h-[85vh] max-w-5xl gap-0 p-0"
        aria-describedby="settings-description"
      >
        <DialogTitle className="sr-only">설정</DialogTitle>
        <DialogDescription id="settings-description" className="sr-only">
          애플리케이션 설정을 관리합니다
        </DialogDescription>
        <div className="flex h-full">
          {/* Left Sidebar */}
          <div className="border-border bg-muted/30 flex w-48 flex-col border-r p-4">
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
                  <tab.icon className="h-4 w-4 flex-shrink-0" />
                  <span className="text-sm font-medium">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Right Content */}
          <div className="relative flex-1 overflow-y-auto p-8">
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
                {activeTab === 'models' && <ModelsContent />}
                {activeTab === 'personalization' && <PersonalizationContent />}
                {activeTab === 'apiKeys' && <ApiKeysContent />}
                {activeTab === 'channels' && <ChannelsContent />}
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

  const toggleSkill = (id: string) => {
    setSkills((prev) =>
      prev.map((skill) => (skill.id === id ? { ...skill, enabled: !skill.enabled } : skill)),
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">스킬 목록</h3>
        <p className="text-muted-foreground text-sm">Heygent가 사용할 수 있는 스킬을 관리합니다</p>
      </div>

      <div className="space-y-3">
        {skills.map((skill) => (
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
      </div>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Models Content
// ────────────────────────────────────────────────────────────────────────────
function ModelsContent() {
  const models = [
    { name: 'GPT-4 Turbo', usage: 1250, limit: 5000, color: '#3b82f6' },
    { name: 'Claude 3 Sonnet', usage: 840, limit: 3000, color: '#8b5cf6' },
    { name: 'Gemini Pro', usage: 320, limit: 2000, color: '#10b981' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">모델</h3>
        <p className="text-muted-foreground text-sm">사용 중인 AI 모델과 사용량을 확인합니다</p>
      </div>

      <div className="space-y-4">
        {models.map((model, i) => {
          const percentage = (model.usage / model.limit) * 100
          return (
            <div key={i} className="bg-muted/30 border-border rounded-xl border p-4">
              <div className="mb-3 flex items-center justify-between">
                <h4 className="text-foreground text-sm font-medium">{model.name}</h4>
                <span className="text-muted-foreground text-xs">
                  {model.usage.toLocaleString()} / {model.limit.toLocaleString()} 요청
                </span>
              </div>
              <div className="bg-muted h-2 overflow-hidden rounded-full">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${percentage}%`,
                    backgroundColor: model.color,
                  }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-muted-foreground text-xs">
                  사용률: {percentage.toFixed(1)}%
                </span>
                <span className="text-muted-foreground text-xs">
                  남은 요청: {(model.limit - model.usage).toLocaleString()}
                </span>
              </div>
            </div>
          )
        })}
      </div>
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
function ApiKeysContent() {
  const [apiKeys, setApiKeys] = useState([
    { id: 'openai', name: 'OpenAI API', value: 'sk-proj-***************', masked: true },
    { id: 'anthropic', name: 'Anthropic API', value: 'sk-ant-***************', masked: true },
    { id: 'github', name: 'GitHub Token', value: '', masked: true },
  ])

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-foreground mb-2 text-xl font-semibold">API 키</h3>
        <p className="text-muted-foreground text-sm">외부 서비스 연동을 위한 API 키를 관리합니다</p>
      </div>

      <div className="space-y-3">
        {apiKeys.map((key) => (
          <div key={key.id} className="bg-muted/30 border-border rounded-xl border p-4">
            <label className="text-foreground mb-2 block text-sm font-medium">{key.name}</label>
            <input
              type={key.masked ? 'password' : 'text'}
              value={key.value}
              onChange={(e) => {
                setApiKeys((prev) =>
                  prev.map((k) => (k.id === key.id ? { ...k, value: e.target.value } : k)),
                )
              }}
              placeholder={`${key.name} 키를 입력하세요`}
              className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/20 w-full rounded-lg border bg-white px-3 py-2 text-sm focus:ring-2 focus:outline-none"
            />
          </div>
        ))}
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
