import { Code, Calendar, Apple, Activity, Bot } from 'lucide-react'
import type { ComponentType } from 'react'

export type MessageRole = 'user' | 'agent'
export type AgentKey = 'code-review' | 'scheduler' | 'wellness' | 'health' | 'main'

export interface AgentMeta {
  name: string
  shortName: string
  color: string
  icon: ComponentType<{ style?: React.CSSProperties; className?: string }>
}

export const agentMeta: Record<AgentKey, AgentMeta> = {
  main: { name: 'Heygent AI', shortName: 'Heygent', color: '#3b82f6', icon: Bot },
  'code-review': {
    name: '코드 리뷰 에이전트',
    shortName: '코드 리뷰',
    color: '#3b82f6',
    icon: Code,
  },
  scheduler: {
    name: '스케줄러 / 알림 에이전트',
    shortName: '스케줄러',
    color: '#8b5cf6',
    icon: Calendar,
  },
  wellness: { name: '식단 & 웰니스 에이전트', shortName: '웰니스', color: '#10b981', icon: Apple },
  health: { name: '건강 데이터 컴패니언', shortName: '건강', color: '#f59e0b', icon: Activity },
}

export interface Message {
  id: string
  role: MessageRole
  agent?: AgentKey
  text: string
  time: string
  /** Optional structured card appended to the message */
  card?: {
    type: 'code' | 'list' | 'stats'
    content: string
  }
}

export interface Session {
  id: string
  title: string
  time: string
  preview: string
  agentKey: AgentKey
  messages: Message[]
}

export const sessions: Session[] = [
  {
    id: 'S-1',
    title: 'Code Review Session',
    time: '오늘 오후 2:30',
    preview: 'PR #245 리뷰 부탁해...',
    agentKey: 'code-review',
    messages: [
      {
        id: 'm1',
        role: 'user',
        time: '오후 2:28',
        text: 'PR #245 리뷰 부탁해. 보안 이슈 있는지도 확인해줘.',
      },
      {
        id: 'm2',
        role: 'agent',
        agent: 'main',
        time: '오후 2:28',
        text: '알겠습니다. 코드 리뷰 에이전트에게 PR #245 분석을 요청할게요.',
      },
      {
        id: 'm3',
        role: 'agent',
        agent: 'code-review',
        time: '오후 2:29',
        text: 'PR #245를 분석 중입니다. 변경된 파일 12개, 추가 347줄, 삭제 89줄 확인했습니다.\n\n분석 결과 총 **3개의 이슈**를 발견했습니다.',
        card: {
          type: 'list',
          content:
            '🔴 심각 (1건)\n• SQL Injection 취약점 — UserController.java:134\n\n🟡 경고 (2건)\n• 하드코딩된 API 키 — config.js:22\n• 누락된 입력값 검증 — FormHelper.ts:78',
        },
      },
      {
        id: 'm4',
        role: 'user',
        time: '오후 2:31',
        text: 'SQL Injection 취약점이 얼마나 심각해? 바로 핫픽스가 필요한 수준이야?',
      },
      {
        id: 'm5',
        role: 'agent',
        agent: 'code-review',
        time: '오후 2:31',
        text: '해당 취약점은 **심각도 높음(High)**으로 분류됩니다.\n\n`UserController.java:134` 라인에서 사용자 입력값이 PreparedStatement 없이 직접 쿼리에 삽입되고 있습니다. 공격자가 인증 우회 및 데이터 유출을 시도할 수 있어 즉시 수정이 권장됩니다.',
        card: {
          type: 'code',
          content:
            '// ❌ 취약한 코드\nString query = "SELECT * FROM users WHERE id=\'" + userId + "\'";\n\n// ✅ 수정 권고\nPreparedStatement ps = conn.prepareStatement(\n  "SELECT * FROM users WHERE id=?"\n);\nps.setString(1, userId);',
        },
      },
      {
        id: 'm6',
        role: 'user',
        time: '오후 2:33',
        text: '수정 PR은 내가 직접 올릴게. 나머지 경고 2건도 코멘트 달아줄 수 있어?',
      },
      {
        id: 'm7',
        role: 'agent',
        agent: 'code-review',
        time: '오후 2:34',
        text: '네, 두 경고 항목에 대해 GitHub PR 코멘트를 자동으로 작성했습니다.\n\n• `config.js:22` — API 키는 환경 변수(`.env`)로 이동할 것을 권고하는 코멘트 추가 완료\n• `FormHelper.ts:78` — Zod 스키마를 활용한 입력 검증 코드 예시 코멘트 추가 완료\n\n전체 리뷰 리포트를 요약해서 드릴까요?',
      },
      { id: 'm8', role: 'user', time: '오후 2:35', text: '아니야 충분해. 고마워!' },
      {
        id: 'm9',
        role: 'agent',
        agent: 'code-review',
        time: '오후 2:35',
        text: '네, 필요하면 언제든지 불러주세요. PR #245 리뷰를 완료로 처리했습니다. ✅',
      },
    ],
  },
  {
    id: 'S-2',
    title: 'Wellness Planning',
    time: '오늘 오전 10:15',
    preview: '건강한 저녁 메뉴 추천해줘...',
    agentKey: 'wellness',
    messages: [
      {
        id: 'm1',
        role: 'user',
        time: '오전 10:14',
        text: '오늘 저녁 건강하게 먹고 싶어. 칼로리 500kcal 이하로 메뉴 추천해줘.',
      },
      {
        id: 'm2',
        role: 'agent',
        agent: 'main',
        time: '오전 10:14',
        text: '식단 & 웰니스 에이전트가 오늘 식사 기록을 분석해서 저녁 메뉴를 추천해드릴게요.',
      },
      {
        id: 'm3',
        role: 'agent',
        agent: 'wellness',
        time: '오전 10:15',
        text: '오늘 아침·점심에서 탄수화물이 다소 높게 나왔어요. 저녁은 단백질 위주로 구성하는 것이 좋을 것 같습니다.\n\n500kcal 이하 저녁 메뉴 **3가지**를 추천드립니다.',
        card: {
          type: 'list',
          content:
            '🥗 두부 샐러드 + 닭가슴살 구이 — 약 380kcal\n  단백질 42g · 탄수화물 18g · 지방 11g\n\n🍱 현미밥 반 공기 + 된장찌개 — 약 420kcal\n  단백질 21g · 탄수화물 52g · 지방 8g\n\n🥩 연어 스테이크 + 브로콜리 — 약 460kcal\n  단백질 38g · 탄수화물 12g · 지방 22g',
        },
      },
      {
        id: 'm4',
        role: 'user',
        time: '오전 10:17',
        text: '첫 번째 메뉴 좋네. 레시피도 알 수 있어?',
      },
      {
        id: 'm5',
        role: 'agent',
        agent: 'wellness',
        time: '오전 10:17',
        text: '두부 샐러드 + 닭가슴살 구이 레시피입니다.',
        card: {
          type: 'list',
          content:
            '재료 (1인분)\n• 닭가슴살 150g, 두부 100g\n• 양상추 50g, 방울토마토 5개\n• 올리브오일 1 tsp, 레몬즙 1 tsp\n\n조리 순서\n1. 닭가슴살에 소금·후추 밑간 후 팬에 굽기 (8분)\n2. 두부는 물기 제거 후 에어프라이어 180°C 10분\n3. 채소 손질 후 드레싱 뿌려 플레이팅',
        },
      },
      {
        id: 'm6',
        role: 'user',
        time: '오전 10:18',
        text: '완벽해! 식사 기록에 저녁 메뉴로 추가해줘.',
      },
      {
        id: 'm7',
        role: 'agent',
        agent: 'wellness',
        time: '오전 10:18',
        text: "오늘 저녁 식사 계획에 '두부 샐러드 + 닭가슴살 구이'를 등록했습니다. 저녁 식사 후 칼로리 기록도 잊지 마세요! 🥗",
      },
    ],
  },
  {
    id: 'S-3',
    title: 'Task Scheduling',
    time: '어제',
    preview: '내일 스탠드업 알림 설정해줘...',
    agentKey: 'scheduler',
    messages: [
      {
        id: 'm1',
        role: 'user',
        time: '어제 오후 9:02',
        text: '내일 오전 스탠드업 알림 설정해줘. 그리고 오후 5시에 퇴근 전 작업 정리 알림도 추가해.',
      },
      {
        id: 'm2',
        role: 'agent',
        agent: 'main',
        time: '어제 오후 9:02',
        text: '스케줄러 에이전트에게 알림 설정을 요청할게요.',
      },
      {
        id: 'm3',
        role: 'agent',
        agent: 'scheduler',
        time: '어제 오후 9:02',
        text: '두 가지 알림을 설정하겠습니다. 스탠드업 알림 시간을 먼저 확인할게요. 몇 시로 설정할까요?',
      },
      { id: 'm4', role: 'user', time: '어제 오후 9:03', text: '오전 10시.' },
      {
        id: 'm5',
        role: 'agent',
        agent: 'scheduler',
        time: '어제 오후 9:03',
        text: '알겠습니다. 두 알림을 모두 설정했습니다.',
        card: {
          type: 'list',
          content:
            '✅ 등록된 알림\n\n⏰ 내일 오전 10:00\n   "일일 스탠드업 회의 시작합니다"\n   반복: 평일 매일\n\n⏰ 내일 오후 5:00\n   "퇴근 전 오늘 작업 내용을 정리하세요"\n   반복: 평일 매일',
        },
      },
      { id: 'm6', role: 'user', time: '어제 오후 9:04', text: '스탠드업 알림은 주말은 빼줘.' },
      {
        id: 'm7',
        role: 'agent',
        agent: 'scheduler',
        time: '어제 오후 9:04',
        text: '수정했습니다. 스탠드업 알림은 **평일(월~금)**에만 울리도록 변경했습니다. 퇴근 알림은 기존 설정을 유지합니다. ✅',
      },
      { id: 'm8', role: 'user', time: '어제 오후 9:05', text: '완벽해. 고마워.' },
      {
        id: 'm9',
        role: 'agent',
        agent: 'scheduler',
        time: '어제 오후 9:05',
        text: '네! 내일 오전 10시에 첫 번째 스탠드업 알림을 보내드릴게요. 좋은 밤 되세요 🌙',
      },
    ],
  },
  {
    id: 'S-4',
    title: 'Health Check-in',
    time: '어제',
    preview: '오늘 걸음 수 어때?...',
    agentKey: 'health',
    messages: [
      { id: 'm1', role: 'user', time: '어제 오후 7:30', text: '오늘 걸음 수 어때? 목표 달성했어?' },
      {
        id: 'm2',
        role: 'agent',
        agent: 'main',
        time: '어제 오후 7:30',
        text: '건강 데이터 컴패니언에게 오늘 활동 데이터를 가져오도록 할게요.',
      },
      {
        id: 'm3',
        role: 'agent',
        agent: 'health',
        time: '어제 오후 7:31',
        text: '오늘 건강 데이터를 조회했습니다.',
        card: {
          type: 'stats',
          content:
            '👟 걸음 수: 7,823보 / 목표 10,000보 (78.2%)\n🔥 소모 칼로리: 312 kcal\n❤️ 평균 심박수: 72 bpm\n😴 어젯밤 수면: 7시간 14분',
        },
      },
      {
        id: 'm4',
        role: 'agent',
        agent: 'health',
        time: '어제 오후 7:31',
        text: '목표까지 **2,177보** 남았습니다. 약 20~25분 정도 가볍게 걸으시면 달성하실 수 있어요!',
      },
      { id: 'm5', role: 'user', time: '어제 오후 7:32', text: '심박수는 정상 범위야?' },
      {
        id: 'm6',
        role: 'agent',
        agent: 'health',
        time: '어제 오후 7:32',
        text: '네, 안정 시 심박수 **72 bpm**은 정상 범위(60~100 bpm)에 해당합니다. 오늘 활동 중 최고 심박수는 138 bpm이었으며, 이 역시 유산소 운동 범위(최대 심박수의 70~85%) 안에 있어 건강한 수치입니다. 👍',
      },
      { id: 'm7', role: 'user', time: '어제 오후 7:34', text: '이번 주 걸음 수 평균도 알려줘.' },
      {
        id: 'm8',
        role: 'agent',
        agent: 'health',
        time: '어제 오후 7:34',
        text: '이번 주(월~어제) 걸음 수 현황입니다.',
        card: {
          type: 'list',
          content:
            '월  9,241보 ✅\n화  10,512보 ✅\n수  6,830보 ❌\n목  8,200보 ❌\n금  7,823보 (진행 중)\n\n📊 현재 주간 평균: 8,521보\n🎯 주간 목표 달성률: 85.2%',
        },
      },
      {
        id: 'm9',
        role: 'user',
        time: '어제 오후 7:35',
        text: '수요일에 많이 못 걸었네. 이번 주 마무리 잘 해야겠다. 고마워!',
      },
      {
        id: 'm10',
        role: 'agent',
        agent: 'health',
        time: '어제 오후 7:35',
        text: '주간 평균이 꽤 좋은 편이에요! 오늘 저녁 산책으로 목표를 채우시면 이번 주 마무리 완벽할 것 같습니다. 화이팅! 💪',
      },
    ],
  },
]
