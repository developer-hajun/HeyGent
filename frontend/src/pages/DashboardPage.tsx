import {
  Sparkles,
  Send,
  Code,
  Calendar,
  Apple,
  Activity,
  CheckCircle2,
  TrendingUp,
  ChevronRight,
  Bot,
  Plus,
  Footprints,
  Moon,
  Dumbbell,
  Mic,
  Repeat,
  Target,
  CalendarCheck,
} from 'lucide-react'
import { motion, AnimatePresence } from 'motion/react'
import { useState } from 'react'
import * as React from 'react'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../components/ui/dialog'
import type { Agent } from '../components/layout/RightPanel'

type EventType = 'event' | 'task' | 'repeat'

const eventTypeConfig = {
  event: {
    label: '일정',
    icon: CalendarCheck,
    defaultColor: { bg: '#3b82f6', border: '#3b82f620', text: '#3b82f6' },
    description: '시간 기반 일정',
  },
  task: {
    label: '할 일',
    icon: Target,
    defaultColor: { bg: '#f59e0b', border: '#f59e0b20', text: '#f59e0b' },
    description: '마감일 있는 할 일',
  },
  repeat: {
    label: '반복',
    icon: Repeat,
    defaultColor: { bg: '#10b981', border: '#10b98120', text: '#10b981' },
    description: '반복 일정',
  },
}

const availableColors = [
  { bg: '#3b82f6', border: '#3b82f620', text: '#3b82f6', name: '파란색' },
  { bg: '#8b5cf6', border: '#8b5cf620', text: '#8b5cf6', name: '보라색' },
  { bg: '#10b981', border: '#10b98120', text: '#10b981', name: '초록색' },
  { bg: '#f59e0b', border: '#f59e0b20', text: '#f59e0b', name: '주황색' },
  { bg: '#ef4444', border: '#ef444420', text: '#ef4444', name: '빨간색' },
  { bg: '#ec4899', border: '#ec489920', text: '#ec4899', name: '핑크색' },
  { bg: '#06b6d4', border: '#06b6d420', text: '#06b6d4', name: '청록색' },
  { bg: '#84cc16', border: '#84cc1620', text: '#84cc16', name: '라임색' },
  { bg: '#f97316', border: '#f9731620', text: '#f97316', name: '오렌지색' },
  { bg: '#a855f7', border: '#a855f720', text: '#a855f7', name: '자주색' },
  { bg: '#14b8a6', border: '#14b8a620', text: '#14b8a6', name: '청록색' },
  { bg: '#fb923c', border: '#fb923c20', text: '#fb923c', name: '코랄색' },
]

// Calendar Widget Component
function CalendarWidget({ onClose }: { onClose: () => void }) {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [eventTitle, setEventTitle] = useState('')
  const [eventTime, setEventTime] = useState('12:00')
  const [eventType, setEventType] = useState<EventType>('event')
  const [eventColor, setEventColor] = useState(eventTypeConfig.event.defaultColor)
  const [repeatType, setRepeatType] = useState<'daily' | 'weekly' | 'custom'>('daily')
  const [repeatDays, setRepeatDays] = useState<number[]>([])
  const [repeatInterval, setRepeatInterval] = useState(1)

  const today = new Date()
  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth()

  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const daysInPrevMonth = new Date(year, month, 0).getDate()
  const firstDayOfMonth = new Date(year, month, 1).getDay()

  const handleTypeChange = (type: EventType) => {
    setEventType(type)
    setEventColor(eventTypeConfig[type].defaultColor)
  }

  const toggleRepeatDay = (day: number) => {
    setRepeatDays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]))
  }

  const handleSubmit = () => {
    if (eventTitle.trim()) {
      const eventData = {
        title: eventTitle,
        date: selectedDate,
        time: eventTime,
        type: eventType,
        color: eventColor,
        ...(eventType === 'repeat' && {
          repeat: {
            type: repeatType,
            days: repeatDays,
            interval: repeatInterval,
          },
        }),
      }
      console.log('New event:', eventData)
      onClose()
    }
  }

  const goToPrevMonth = () => {
    setCurrentMonth(new Date(year, month - 1, 1))
  }

  const goToNextMonth = () => {
    setCurrentMonth(new Date(year, month + 1, 1))
  }

  // Mock existing events for display on calendar
  const existingEvents = [
    { day: today.getDate(), title: '팀 회의', color: '#3b82f6' },
    { day: today.getDate(), title: '병원 예약', color: '#8b5cf6' },
    { day: today.getDate() + 1, title: '프로젝트 마감', color: '#f59e0b' },
    { day: today.getDate() + 2, title: '운동하기', color: '#10b981' },
    { day: today.getDate() + 5, title: '저녁 약속', color: '#ec4899' },
  ]

  return (
    <div className="p-3">
      <h2 className="text-foreground mb-2 text-xs font-semibold">일정 등록</h2>

      {/* Calendar - Moved to top */}
      <div className="mb-2.5">
        <div className="mb-2 flex items-center justify-between">
          <button onClick={goToPrevMonth} className="hover:bg-muted rounded p-1 transition-colors">
            <ChevronRight className="text-muted-foreground h-3.5 w-3.5 rotate-180" />
          </button>
          <h3 className="text-foreground text-xs font-semibold">
            {year}년 {month + 1}월
          </h3>
          <button onClick={goToNextMonth} className="hover:bg-muted rounded p-1 transition-colors">
            <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
          </button>
        </div>

        <div className="border-border overflow-hidden rounded-lg border">
          <div className="grid grid-cols-7">
            {['일', '월', '화', '수', '목', '금', '토'].map((day, i) => (
              <div
                key={i}
                className="text-muted-foreground bg-muted/30 border-border border-b py-1.5 text-center text-[9px] font-semibold"
              >
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {/* Previous month days */}
            {Array.from({ length: firstDayOfMonth }, (_, i) => {
              const day = daysInPrevMonth - firstDayOfMonth + i + 1
              return (
                <div
                  key={`prev-${i}`}
                  className="bg-muted/5 text-muted-foreground/40 border-border min-h-[42px] border-r border-b p-1 text-[10px] last:border-r-0"
                >
                  {day}
                </div>
              )
            })}

            {/* Current month days */}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1
              const isToday =
                today.getDate() === day &&
                today.getMonth() === month &&
                today.getFullYear() === year
              const isSelected =
                selectedDate.getDate() === day &&
                selectedDate.getMonth() === month &&
                selectedDate.getFullYear() === year
              const dayEvents =
                month === today.getMonth() && year === today.getFullYear()
                  ? existingEvents.filter((e) => e.day === day)
                  : []

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(new Date(year, month, day))}
                  className={`border-border relative flex min-h-[42px] flex-col items-start border-r border-b p-1 text-[10px] transition-colors last:border-r-0 ${
                    isSelected ? 'bg-primary/10' : 'hover:bg-muted/30 bg-white'
                  }`}
                >
                  <span
                    className={`flex-shrink-0 ${
                      isToday
                        ? 'bg-primary flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white'
                        : isSelected
                          ? 'text-primary font-semibold'
                          : 'text-foreground'
                    }`}
                  >
                    {day}
                  </span>
                  <div className="mt-0.5 w-full space-y-0.5">
                    {dayEvents.slice(0, 2).map((event, idx) => (
                      <div
                        key={idx}
                        className="truncate rounded px-0.5 py-0.5 text-[7px] leading-tight font-medium text-white"
                        style={{ backgroundColor: event.color }}
                      >
                        {event.title}
                      </div>
                    ))}
                    {dayEvents.length > 2 && (
                      <div className="text-muted-foreground text-[7px] font-medium">
                        +{dayEvents.length - 2}
                      </div>
                    )}
                  </div>
                </button>
              )
            })}

            {/* Next month days */}
            {Array.from({ length: 42 - daysInMonth - firstDayOfMonth }, (_, i) => {
              const day = i + 1
              return (
                <div
                  key={`next-${i}`}
                  className="bg-muted/5 text-muted-foreground/40 border-border min-h-[42px] border-r border-b p-1 text-[10px] last:border-r-0"
                >
                  {day}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Event Type Selection */}
      <div className="mb-2">
        <label className="text-foreground mb-1 block text-[10px] font-medium">일정 유형</label>
        <div className="grid grid-cols-3 gap-1">
          {(Object.keys(eventTypeConfig) as EventType[]).map((type) => {
            const config = eventTypeConfig[type]
            const Icon = config.icon
            const isSelected = eventType === type
            return (
              <button
                key={type}
                onClick={() => handleTypeChange(type)}
                className={`rounded-md p-1.5 transition-all ${
                  isSelected ? 'opacity-100' : 'opacity-30'
                }`}
                style={{ backgroundColor: config.defaultColor.bg }}
              >
                <Icon className="mx-auto mb-0.5 h-3 w-3 text-white" />
                <p className="text-[9px] font-medium text-white">{config.label}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Color Selection */}
      <div className="mb-2">
        <label className="text-foreground mb-1 block text-[10px] font-medium">컬러</label>
        <div className="flex flex-wrap gap-1">
          {availableColors.map((color, i) => (
            <button
              key={i}
              onClick={() => setEventColor(color)}
              className={`h-5 w-5 rounded transition-all ${
                eventColor.bg === color.bg
                  ? 'ring-foreground/20 scale-105 ring-2 ring-offset-1'
                  : 'hover:scale-105'
              }`}
              style={{ backgroundColor: color.bg }}
              title={color.name}
            />
          ))}
        </div>
      </div>

      {/* Event Details */}
      <div className="mb-2 space-y-1.5">
        <div>
          <label className="text-foreground mb-0.5 block text-[10px] font-medium">제목</label>
          <input
            type="text"
            value={eventTitle}
            onChange={(e) => setEventTitle(e.target.value)}
            placeholder={`${eventTypeConfig[eventType].label} 이름 입력`}
            className="border-border text-foreground placeholder:text-muted-foreground focus:ring-primary/30 w-full rounded-md border bg-white px-2 py-1.5 text-[11px] focus:ring-1 focus:outline-none"
          />
        </div>

        <div>
          <label className="text-foreground mb-0.5 block text-[10px] font-medium">
            {eventType === 'event' ? '시간' : eventType === 'task' ? '마감 시간' : '시작 시간'}
          </label>
          <input
            type="time"
            value={eventTime}
            onChange={(e) => setEventTime(e.target.value)}
            className="border-border text-foreground focus:ring-primary/30 w-full rounded-md border bg-white px-2 py-1.5 text-[11px] focus:ring-1 focus:outline-none"
          />
        </div>
      </div>

      {/* Repeat Options */}
      {eventType === 'repeat' && (
        <div className="bg-muted/30 border-border mb-2 rounded-md border p-2">
          <label className="text-foreground mb-1 block text-[10px] font-medium">반복 설정</label>

          <div className="space-y-1.5">
            {/* Repeat Type Selection */}
            <div className="flex gap-1">
              <button
                onClick={() => setRepeatType('daily')}
                className={`flex-1 rounded px-2 py-1 text-[9px] font-medium transition-colors ${
                  repeatType === 'daily'
                    ? 'bg-primary text-white'
                    : 'border-border text-foreground hover:bg-muted border bg-white'
                }`}
              >
                매일
              </button>
              <button
                onClick={() => setRepeatType('weekly')}
                className={`flex-1 rounded px-2 py-1 text-[9px] font-medium transition-colors ${
                  repeatType === 'weekly'
                    ? 'bg-primary text-white'
                    : 'border-border text-foreground hover:bg-muted border bg-white'
                }`}
              >
                요일 선택
              </button>
              <button
                onClick={() => setRepeatType('custom')}
                className={`flex-1 rounded px-2 py-1 text-[9px] font-medium transition-colors ${
                  repeatType === 'custom'
                    ? 'bg-primary text-white'
                    : 'border-border text-foreground hover:bg-muted border bg-white'
                }`}
              >
                주기
              </button>
            </div>

            {/* Weekly: Day Selection */}
            {repeatType === 'weekly' && (
              <div className="grid grid-cols-7 gap-0.5">
                {['일', '월', '화', '수', '목', '금', '토'].map((day, i) => (
                  <button
                    key={i}
                    onClick={() => toggleRepeatDay(i)}
                    className={`h-6 rounded text-[9px] font-medium transition-colors ${
                      repeatDays.includes(i)
                        ? 'bg-primary text-white'
                        : 'border-border text-foreground hover:bg-muted border bg-white'
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
            )}

            {/* Custom: Interval Selection */}
            {repeatType === 'custom' && (
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min="1"
                  max="365"
                  value={repeatInterval}
                  onChange={(e) => setRepeatInterval(parseInt(e.target.value) || 1)}
                  className="border-border focus:ring-primary/30 w-12 rounded border bg-white px-1.5 py-1 text-center text-[10px] focus:ring-1 focus:outline-none"
                />
                <span className="text-foreground text-[10px]">일마다 반복</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-1.5">
        <button
          onClick={onClose}
          className="bg-muted text-foreground hover:bg-muted/80 flex-1 rounded-md px-3 py-1.5 text-[10px] font-medium transition-colors"
        >
          취소
        </button>
        <button
          onClick={handleSubmit}
          disabled={!eventTitle.trim()}
          className="flex-1 rounded-md px-3 py-1.5 text-[10px] font-medium text-white transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          style={{ backgroundColor: eventColor.bg }}
        >
          등록
        </button>
      </div>
    </div>
  )
}

// Month Calendar Component
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function MonthCalendar({
  events,
}: {
  events: Array<{
    id: number
    title: string
    time: string
    date: string
    type: string
    color: string
  }>
}) {
  const today = new Date()
  const [currentDate, setCurrentDate] = useState(today)

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const daysInPrevMonth = new Date(year, month, 0).getDate()
  const firstDayOfMonth = new Date(year, month, 1).getDay()

  const goToPrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1))
  }

  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1))
  }

  // Mock existing events for display on calendar
  const existingEvents = [
    { day: today.getDate(), title: '팀 회의', color: '#3b82f6' },
    { day: today.getDate(), title: '병원 예약', color: '#8b5cf6' },
    { day: today.getDate() + 1, title: '프로젝트 마감', color: '#f59e0b' },
    { day: today.getDate() + 2, title: '운동하기', color: '#10b981' },
  ]

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <button onClick={goToPrevMonth} className="hover:bg-muted rounded p-1 transition-colors">
          <ChevronRight className="text-muted-foreground h-3.5 w-3.5 rotate-180" />
        </button>
        <h3 className="text-foreground text-xs font-semibold">
          {year}년 {month + 1}월
        </h3>
        <button onClick={goToNextMonth} className="hover:bg-muted rounded p-1 transition-colors">
          <ChevronRight className="text-muted-foreground h-3.5 w-3.5" />
        </button>
      </div>

      <div>
        <div className="mb-1 grid grid-cols-7 gap-1">
          {['일', '월', '화', '수', '목', '금', '토'].map((day, i) => (
            <div key={i} className="text-muted-foreground py-1 text-center text-[9px] font-medium">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {/* Previous month days */}
          {Array.from({ length: firstDayOfMonth }, (_, i) => {
            const day = daysInPrevMonth - firstDayOfMonth + i + 1
            return (
              <div
                key={`prev-${i}`}
                className="text-muted-foreground/30 hover:bg-muted/20 flex aspect-square cursor-pointer flex-col items-center justify-start rounded-lg p-1 text-[10px] transition-colors"
              >
                <span className="mb-0.5">{day}</span>
              </div>
            )
          })}

          {/* Current month days */}
          {Array.from({ length: daysInMonth }, (_, i) => {
            const day = i + 1
            const isToday =
              today.getDate() === day && today.getMonth() === month && today.getFullYear() === year
            const dayEvents =
              month === today.getMonth() && year === today.getFullYear()
                ? existingEvents.filter((e) => e.day === day)
                : []

            return (
              <div
                key={day}
                className="hover:bg-muted/30 flex aspect-square cursor-pointer flex-col items-center justify-start rounded-lg p-1 transition-colors"
              >
                <span
                  className={`mb-0.5 text-[10px] ${
                    isToday
                      ? 'bg-primary flex h-5 w-5 items-center justify-center rounded-full font-bold text-white'
                      : 'text-foreground'
                  }`}
                >
                  {day}
                </span>
                {dayEvents.length > 0 && (
                  <div className="mt-0.5 flex gap-0.5">
                    {dayEvents.slice(0, 3).map((event, idx) => (
                      <div
                        key={idx}
                        className="h-1 w-1 rounded-full"
                        style={{ backgroundColor: event.color }}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })}

          {/* Next month days */}
          {Array.from({ length: 42 - daysInMonth - firstDayOfMonth }, (_, i) => {
            const day = i + 1
            return (
              <div
                key={`next-${i}`}
                className="text-muted-foreground/30 hover:bg-muted/20 flex aspect-square cursor-pointer flex-col items-center justify-start rounded-lg p-1 text-[10px] transition-colors"
              >
                <span className="mb-0.5">{day}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

const suggestedPrompts = [
  {
    text: '이 PR 검토해줘',
    icon: Code,
    color: 'text-blue-500',
    bg: 'hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600',
  },
  {
    text: '오후 5시에 알려줘',
    icon: Calendar,
    color: 'text-violet-500',
    bg: 'hover:bg-violet-50 hover:border-violet-200 hover:text-violet-600',
  },
  {
    text: '저녁 메뉴 추천해줘',
    icon: Apple,
    color: 'text-emerald-500',
    bg: 'hover:bg-emerald-50 hover:border-emerald-200 hover:text-emerald-600',
  },
  {
    text: '운동 끝나면 알려줘',
    icon: Activity,
    color: 'text-orange-500',
    bg: 'hover:bg-orange-50 hover:border-orange-200 hover:text-orange-600',
  },
]

const agents = [
  {
    name: '코드 리뷰',
    icon: Code,
    status: 'idle' as const,
    statusColor: 'text-muted-foreground',
    dotColor: 'bg-muted-foreground',
    accent: '#3b82f6',
    description: 'PR 분석 및 코드 품질 검토',
  },
  {
    name: '일정 관리',
    icon: Calendar,
    status: 'running' as const,
    statusColor: 'text-primary',
    dotColor: 'bg-primary',
    accent: '#8b5cf6',
    description: '스마트 작업 일정 관리',
  },
  {
    name: '헬스케어',
    icon: Activity,
    status: 'ready' as const,
    statusColor: 'text-emerald-500',
    dotColor: 'bg-emerald-500',
    accent: '#10b981',
    description: '건강 데이터 및 운동 추적',
  },
]

const recentResults = [
  {
    agent: '코드 리뷰 에이전트',
    task: 'PR #243 검토 — 3개 이슈 발견',
    time: '2분 전',
    icon: Code,
    accent: '#3b82f6',
  },
  {
    agent: '식단 & 웰니스',
    task: '저녁 메뉴 추천 완료',
    time: '15분 전',
    icon: Apple,
    accent: '#10b981',
  },
  {
    agent: '건강 데이터 컴패니언',
    task: '오늘 걸음수 목표 달성',
    time: '1시간 전',
    icon: Activity,
    accent: '#f59e0b',
  },
]

const upcomingReminders = [
  { id: 1, title: '팀 회의', time: '오후 3:00', date: '오늘', type: 'event', color: '#3b82f6' },
  { id: 2, title: '병원 예약', time: '오후 5:30', date: '오늘', type: 'event', color: '#8b5cf6' },
  {
    id: 3,
    title: '프로젝트 마감',
    time: '오전 10:00',
    date: '내일',
    type: 'task',
    color: '#f59e0b',
  },
  { id: 4, title: '운동하기', time: '오전 7:00', date: '매일', type: 'repeat', color: '#10b981' },
]

const healthInsights = [
  {
    message: '민수님, 오늘 수면 시간이 3시간밖에 안 되네요. 오늘은 일찍 주무세요!',
    icon: Moon,
    color: '#8b5cf6',
    type: 'warning',
    data: '3시간',
  },
  {
    message: '목표 걸음수 10,000보를 달성하셨어요! 훌륭합니다 👏',
    icon: Footprints,
    color: '#3b82f6',
    type: 'achievement',
    data: '10,420보',
  },
  {
    message: '오늘 45분 운동하셨네요. 꾸준히 유지하세요!',
    icon: Dumbbell,
    color: '#10b981',
    type: 'good',
    data: '45분',
  },
]

interface MainWorkspaceProps {
  onAgentSelect?: (agent: Agent) => void
}

export function DashboardPage({ onAgentSelect }: MainWorkspaceProps = {}) {
  const [inputValue, setInputValue] = useState('')
  const [calendarOpen, setCalendarOpen] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [reminderView, setReminderView] = useState<'list' | 'calendar'>('list')

  const currentHour = new Date().getHours()
  const greeting =
    currentHour < 12 ? '좋은 아침입니다' : currentHour < 17 ? '좋은 오후입니다' : '좋은 저녁입니다'

  const handleVoiceInput = () => {
    setIsRecording(!isRecording)
    // Voice recording logic would go here
    if (!isRecording) {
      console.log('음성 녹음 시작')
    } else {
      console.log('음성 녹음 중지')
    }
  }

  const handleAgentClick = (agent: (typeof agents)[0]) => {
    onAgentSelect?.(agent)
  }

  return (
    <div className="bg-background flex-1 overflow-x-hidden overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-10 px-8 py-10">
        {/* ── Hero Greeting ── */}
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="space-y-1"
        >
          <div className="mb-4 flex items-center gap-2.5">
            <div className="from-primary to-chart-5 flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br shadow-sm">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-muted-foreground text-xs">{greeting}, Alex</p>
            </div>
            <div className="ml-auto flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
              <span className="text-xs font-medium text-emerald-600">모든 에이전트 온라인</span>
            </div>
          </div>
        </motion.div>

        {/* ── Input Area ── */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05 }}
        >
          <div className="border-border overflow-hidden rounded-2xl border bg-white shadow-sm transition-shadow duration-200 hover:shadow-md">
            {/* Input row */}
            <div className="flex items-center gap-3 px-5 py-4">
              <Sparkles className="text-primary/60 h-5 w-5 flex-shrink-0" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="무엇이든 물어보세요. 적합한 전문 에이전트에게 연결해 드릴게요!"
                className="text-foreground placeholder:text-muted-foreground flex-1 bg-transparent outline-none"
                style={{ fontSize: '15px' }}
              />
              <button
                onClick={handleVoiceInput}
                className={`flex-shrink-0 rounded-xl p-2.5 transition-colors ${
                  isRecording
                    ? 'animate-pulse bg-red-500 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                title="음성 입력"
              >
                <Mic className="h-4 w-4" />
              </button>
              <button
                className="bg-primary hover:bg-primary/90 flex-shrink-0 rounded-xl p-2 text-white transition-colors disabled:opacity-40"
                disabled={!inputValue.trim()}
              >
                <Send className="h-4 w-4" />
              </button>
            </div>

            {/* Divider */}
            <div className="border-border/60 mx-5 border-t" />

            {/* Prompt chips */}
            <div className="flex flex-wrap items-center gap-2 px-5 py-3">
              {suggestedPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInputValue(prompt.text)}
                  className={`bg-muted text-muted-foreground flex items-center gap-1.5 rounded-lg border border-transparent px-3 py-1.5 transition-all duration-150 ${prompt.bg}`}
                  style={{ fontSize: '13px' }}
                >
                  <prompt.icon className="h-3.5 w-3.5" />
                  <span>{prompt.text}</span>
                </button>
              ))}
            </div>
          </div>
        </motion.div>

        {/* ── Reminders & Healthcare Grid ── */}
        <div className="grid grid-cols-2 gap-4">
          {/* Upcoming Reminders & Calendar */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div className="border-border h-full rounded-2xl border bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-50">
                    <Calendar className="h-4 w-4 text-violet-600" />
                  </div>
                  <h3 className="text-foreground text-sm font-semibold">
                    {reminderView === 'list' ? '예정된 리마인더' : '달력'}
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <div className="bg-muted flex items-center rounded-lg p-0.5">
                    <button
                      onClick={() => setReminderView('list')}
                      className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                        reminderView === 'list'
                          ? 'text-foreground bg-white shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      목록
                    </button>
                    <button
                      onClick={() => setReminderView('calendar')}
                      className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                        reminderView === 'calendar'
                          ? 'text-foreground bg-white shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      달력
                    </button>
                  </div>
                  <button
                    onClick={() => setCalendarOpen(true)}
                    className="bg-primary hover:bg-primary/90 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-white transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    등록
                  </button>
                </div>
              </div>

              <AnimatePresence mode="wait">
                {reminderView === 'list' ? (
                  <motion.div
                    key="list"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-2"
                  >
                    {upcomingReminders.map((reminder, i) => {
                      const typeIcon =
                        reminder.type === 'event'
                          ? CalendarCheck
                          : reminder.type === 'task'
                            ? Target
                            : Repeat
                      return (
                        <motion.div
                          key={reminder.id}
                          initial={{ opacity: 0, x: -6 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="bg-muted/30 hover:bg-muted/50 hover:border-border flex cursor-pointer items-center gap-3 rounded-xl border border-transparent p-3 transition-colors"
                        >
                          <div
                            className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg"
                            style={{ backgroundColor: `${reminder.color}15` }}
                          >
                            {React.createElement(typeIcon, {
                              className: 'w-4 h-4',
                              style: { color: reminder.color },
                            })}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-foreground truncate text-sm font-medium">
                              {reminder.title}
                            </p>
                            <p className="text-muted-foreground text-xs">
                              {reminder.date} · {reminder.time}
                            </p>
                          </div>
                          <div
                            className="h-2 w-2 flex-shrink-0 rounded-full"
                            style={{ backgroundColor: reminder.color }}
                          />
                        </motion.div>
                      )
                    })}
                  </motion.div>
                ) : (
                  <motion.div
                    key="calendar"
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    transition={{ duration: 0.2 }}
                  >
                    <MonthCalendar events={upcomingReminders} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>

          {/* Healthcare Dashboard */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.12 }}
          >
            <div className="border-border h-full rounded-2xl border bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50">
                  <Activity className="h-4 w-4 text-emerald-600" />
                </div>
                <h3 className="text-foreground text-sm font-semibold">헬스케어</h3>
              </div>

              <div className="space-y-2.5">
                {healthInsights.map((insight, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + i * 0.05 }}
                    className={`rounded-xl border p-3 transition-colors ${
                      insight.type === 'warning'
                        ? 'border-orange-200/50 bg-orange-50/50'
                        : insight.type === 'achievement'
                          ? 'border-blue-200/50 bg-blue-50/50'
                          : 'border-emerald-200/50 bg-emerald-50/50'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg"
                        style={{ backgroundColor: `${insight.color}20` }}
                      >
                        <insight.icon className="h-4 w-4" style={{ color: insight.color }} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-foreground text-sm leading-relaxed">{insight.message}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className="text-xs font-medium" style={{ color: insight.color }}>
                            {insight.data}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* Calendar Dialog */}
        <Dialog open={calendarOpen} onOpenChange={setCalendarOpen}>
          <DialogContent
            className="max-w-[380px] p-0 [&>button]:hidden"
            aria-describedby="calendar-description"
          >
            <DialogTitle className="sr-only">일정 등록</DialogTitle>
            <DialogDescription id="calendar-description" className="sr-only">
              새로운 일정을 등록하세요
            </DialogDescription>
            <CalendarWidget onClose={() => setCalendarOpen(false)} />
          </DialogContent>
        </Dialog>

        {/* ── Available Agents ── */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-foreground text-sm font-semibold">전문 에이전트</h2>
            <button className="text-primary hover:text-primary/80 flex items-center gap-1 text-xs transition-colors">
              전체 보기 <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {agents.map((agent, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + i * 0.04 }}
                className="border-border hover:border-primary/30 group relative rounded-xl border bg-white p-4 transition-all duration-150 hover:shadow-sm"
              >
                {/* Add to Right Panel Button */}
                <button
                  onClick={() => handleAgentClick(agent)}
                  className="border-border hover:bg-primary hover:border-primary absolute top-2 right-2 flex items-center gap-1.5 rounded-md border bg-white px-2 py-1 opacity-0 shadow-sm transition-colors group-hover:opacity-100 hover:text-white"
                  title="우측 모달로 추가"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span className="text-xs font-medium">우측 모달로 추가</span>
                </button>

                <div
                  className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ backgroundColor: `${agent.accent}14` }}
                >
                  <agent.icon className="h-5 w-5" style={{ color: agent.accent }} />
                </div>
                <p className="text-foreground mb-1 text-sm leading-snug font-semibold">
                  {agent.name}
                </p>
                <p className="text-muted-foreground mb-2 text-xs leading-snug">
                  {agent.description}
                </p>
                <div className="flex items-center gap-1.5">
                  <div
                    className={`h-1.5 w-1.5 rounded-full ${agent.dotColor} ${agent.status === 'running' ? 'animate-pulse' : ''}`}
                  />
                  <span className={`text-xs ${agent.statusColor}`}>
                    {agent.status === 'running'
                      ? '실행 중'
                      : agent.status === 'ready'
                        ? '준비됨'
                        : '대기 중'}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* ── Recent Activity ── */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-foreground text-sm font-semibold">최근 활동</h2>
            <div className="flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-xs font-medium text-emerald-500">오늘 27개 완료</span>
            </div>
          </div>
          <div className="space-y-2">
            {recentResults.map((result, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                className="border-border hover:border-primary/20 flex cursor-pointer items-center gap-3 rounded-xl border bg-white p-4 transition-all duration-150 hover:shadow-sm"
              >
                <div
                  className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl"
                  style={{ backgroundColor: `${result.accent}14` }}
                >
                  <result.icon
                    className="h-4.5 w-4.5"
                    style={{ color: result.accent, width: '18px', height: '18px' }}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-medium">{result.task}</p>
                  <p className="text-muted-foreground text-xs">{result.agent}</p>
                </div>
                <div className="flex flex-shrink-0 items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-muted-foreground text-xs">{result.time}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Bottom spacer */}
        <div className="h-4" />
      </div>
    </div>
  )
}
