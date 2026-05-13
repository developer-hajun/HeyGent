import { create } from 'zustand'
import type {
  AgentActivityStatus,
  AgentRuntime,
  AgentVisualizationInfo,
  TaskStatus,
  VisualizationTask,
} from '@/components/office/types'

export type { AgentActivityStatus, AgentVisualizationInfo, TaskStatus, VisualizationTask }

interface AgentVisualizationState {
  agentInfoMap: Record<string, AgentVisualizationInfo>
  selectedAgentId: string | null
  // 페이지 이동 후 재진입 시 에이전트 위치/상태 유지용 런타임 상태
  agentRuntimes: AgentRuntime[]
  spawnedKeys: string[]
  setAgentInfoMap: (map: Record<string, AgentVisualizationInfo>) => void
  updateAgentInfo: (agentId: string, updates: Partial<AgentVisualizationInfo>) => void
  selectAgent: (agentId: string | null) => void
  setAgentRuntimes: (updater: AgentRuntime[] | ((prev: AgentRuntime[]) => AgentRuntime[])) => void
  addSpawnedKey: (id: string) => void
}

// mock 데이터 — 백엔드 API 연동 전 임시. spriteId(agentId)는 AGENT_CONFIGS의 id와 일치해야 함.
const MOCK_AGENTS: AgentVisualizationInfo[] = [
  {
    agentId: 'agent01',
    name: '김준혁',
    role: '백엔드 개발자',
    skills: ['Python', 'FastAPI', 'PostgreSQL', 'Docker'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-001',
      title: 'REST API 설계',
      description: '사용자 인증 및 세션 관리를 위한 API 엔드포인트 설계 및 문서화',
      status: 'in_progress',
      startedAt: '2026-05-11T09:00:00',
    },
    taskHistory: [
      {
        taskId: 'h-001',
        title: '데이터베이스 스키마 설계',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T17:00:00',
      },
      {
        taskId: 'h-002',
        title: '개발 환경 구성',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T11:00:00',
      },
      {
        taskId: 'h-003',
        title: '요구사항 분석',
        description: '',
        status: 'completed',
        completedAt: '2026-05-09T16:00:00',
      },
    ],
  },
  {
    agentId: 'agent02',
    name: '이서연',
    role: '프론트엔드 개발자',
    skills: ['React', 'TypeScript', 'Tailwind CSS', 'Zustand'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-002',
      title: '에이전트 상태 UI 개발',
      description: '실시간 에이전트 상태를 시각화하는 페이지 컴포넌트 구현',
      status: 'in_progress',
      startedAt: '2026-05-11T09:30:00',
    },
    taskHistory: [
      {
        taskId: 'h-011',
        title: '오피스 맵 컴포넌트 구현',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T18:00:00',
      },
      {
        taskId: 'h-012',
        title: '스프라이트 애니메이션 구현',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T14:00:00',
      },
    ],
  },
  {
    agentId: 'agent03',
    name: '박민준',
    role: 'AI 엔지니어',
    skills: ['LLM', 'LangChain', 'Python', 'Vector DB'],
    activityStatus: 'resting',
    currentTask: undefined,
    taskHistory: [
      {
        taskId: 'h-021',
        title: '에이전트 프롬프트 최적화',
        description: '',
        status: 'completed',
        completedAt: '2026-05-11T08:30:00',
      },
      {
        taskId: 'h-022',
        title: 'RAG 파이프라인 구축',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T17:30:00',
      },
      {
        taskId: 'h-023',
        title: '임베딩 모델 선정',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T10:00:00',
      },
    ],
  },
  {
    agentId: 'agent04',
    name: '최다은',
    role: '데이터 분석가',
    skills: ['Python', 'Pandas', 'SQL', 'Tableau'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-004',
      title: '사용자 행동 데이터 분석',
      description: '세션 로그 기반 사용자 패턴 분석 및 인사이트 도출',
      status: 'in_progress',
      startedAt: '2026-05-11T10:00:00',
    },
    taskHistory: [
      {
        taskId: 'h-031',
        title: '데이터 수집 파이프라인 구축',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T16:00:00',
      },
      {
        taskId: 'h-032',
        title: 'KPI 정의',
        description: '',
        status: 'completed',
        completedAt: '2026-05-09T15:00:00',
      },
    ],
  },
  {
    agentId: 'agent05',
    name: '정하준',
    role: 'QA 엔지니어',
    skills: ['테스트 자동화', 'Selenium', 'Jest', 'Cypress'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-005',
      title: 'E2E 테스트 작성',
      description: '에이전트 시각화 페이지 E2E 테스트 케이스 작성 및 실행',
      status: 'in_progress',
      startedAt: '2026-05-11T09:15:00',
    },
    taskHistory: [
      {
        taskId: 'h-041',
        title: '테스트 전략 수립',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T15:00:00',
      },
      {
        taskId: 'h-042',
        title: '단위 테스트 작성',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T12:00:00',
      },
    ],
  },
  {
    agentId: 'agent06',
    name: '윤지민',
    role: 'DevOps 엔지니어',
    skills: ['Kubernetes', 'Docker', 'CI/CD', 'AWS'],
    activityStatus: 'resting',
    currentTask: undefined,
    taskHistory: [
      {
        taskId: 'h-051',
        title: 'CI/CD 파이프라인 구축',
        description: '',
        status: 'completed',
        completedAt: '2026-05-11T08:00:00',
      },
      {
        taskId: 'h-052',
        title: '컨테이너 오케스트레이션 설정',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T17:00:00',
      },
      {
        taskId: 'h-053',
        title: '모니터링 시스템 구축',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T13:00:00',
      },
    ],
  },
  {
    agentId: 'agent07',
    name: '강소율',
    role: 'UX 디자이너',
    skills: ['Figma', 'UI/UX', '사용자 리서치', '프로토타이핑'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-007',
      title: '대시보드 UI 개선안',
      description: '사용자 피드백 기반 대시보드 개선 와이어프레임 제작',
      status: 'in_progress',
      startedAt: '2026-05-11T10:30:00',
    },
    taskHistory: [
      {
        taskId: 'h-061',
        title: '사용자 인터뷰 진행',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T16:00:00',
      },
      {
        taskId: 'h-062',
        title: '디자인 시스템 정의',
        description: '',
        status: 'completed',
        completedAt: '2026-05-09T17:00:00',
      },
    ],
  },
  {
    agentId: 'agent08',
    name: '임도현',
    role: '비즈니스 애널리스트',
    skills: ['비즈니스 분석', 'Excel', 'PowerPoint', '시장 조사'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-008',
      title: '경쟁사 분석 보고서',
      description: '주요 경쟁사 제품 기능 및 시장 포지션 비교 분석',
      status: 'in_progress',
      startedAt: '2026-05-11T09:45:00',
    },
    taskHistory: [
      {
        taskId: 'h-071',
        title: '시장 규모 조사',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T17:30:00',
      },
      {
        taskId: 'h-072',
        title: '고객 세그먼트 분석',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T14:00:00',
      },
    ],
  },
  {
    agentId: 'agent09',
    name: '한수빈',
    role: '프로젝트 매니저',
    skills: ['프로젝트 관리', 'Jira', 'Scrum', '이해관계자 관리'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-009',
      title: '스프린트 계획 수립',
      description: '다음 스프린트 백로그 정리 및 팀원 업무 배분',
      status: 'in_progress',
      startedAt: '2026-05-11T09:00:00',
    },
    taskHistory: [
      {
        taskId: 'h-081',
        title: '스프린트 리뷰 진행',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T16:00:00',
      },
      {
        taskId: 'h-082',
        title: '팀 회고 미팅 진행',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T15:00:00',
      },
      {
        taskId: 'h-083',
        title: '이해관계자 보고',
        description: '',
        status: 'completed',
        completedAt: '2026-05-09T17:00:00',
      },
    ],
  },
  {
    agentId: 'ceo',
    name: 'CEO',
    role: '최고경영자',
    skills: ['전략 기획', '리더십', '의사결정', '비즈니스 개발'],
    activityStatus: 'working',
    currentTask: {
      taskId: 'task-ceo',
      title: '분기 전략 검토',
      description: '각 팀의 분기별 성과 및 다음 분기 전략 방향 검토',
      status: 'in_progress',
      startedAt: '2026-05-11T08:00:00',
    },
    taskHistory: [
      {
        taskId: 'h-ceo-1',
        title: '투자자 미팅',
        description: '',
        status: 'completed',
        completedAt: '2026-05-09T17:00:00',
      },
      {
        taskId: 'h-ceo-2',
        title: '로드맵 수립',
        description: '',
        status: 'completed',
        completedAt: '2026-05-08T16:00:00',
      },
    ],
  },
  {
    agentId: 'agent10',
    name: '오채원',
    role: '리서처',
    skills: ['기술 리서치', '논문 분석', 'Python', '실험 설계'],
    activityStatus: 'resting',
    currentTask: undefined,
    taskHistory: [
      {
        taskId: 'h-091',
        title: '최신 LLM 논문 조사',
        description: '',
        status: 'completed',
        completedAt: '2026-05-11T08:00:00',
      },
      {
        taskId: 'h-092',
        title: '벤치마크 실험 설계',
        description: '',
        status: 'completed',
        completedAt: '2026-05-10T17:00:00',
      },
    ],
  },
]

export function createMockAgentInfoMap(): Record<string, AgentVisualizationInfo> {
  return Object.fromEntries(MOCK_AGENTS.map((info) => [info.agentId, info]))
}

export const useAgentVisualizationStore = create<AgentVisualizationState>((set) => ({
  agentInfoMap: {},
  selectedAgentId: null,
  agentRuntimes: [],
  spawnedKeys: [],

  setAgentInfoMap: (map) => set({ agentInfoMap: map }),

  updateAgentInfo: (agentId, updates) =>
    set((state) => {
      const existing = state.agentInfoMap[agentId] ?? {
        agentId,
        name: agentId,
        role: '',
        skills: [],
        activityStatus: 'inactive' as AgentActivityStatus,
        currentTask: undefined,
        taskHistory: [],
      }
      return { agentInfoMap: { ...state.agentInfoMap, [agentId]: { ...existing, ...updates } } }
    }),

  selectAgent: (agentId) => set({ selectedAgentId: agentId }),

  setAgentRuntimes: (updater) =>
    set((state) => ({
      agentRuntimes: typeof updater === 'function' ? updater(state.agentRuntimes) : updater,
    })),

  addSpawnedKey: (id) =>
    set((state) => ({
      spawnedKeys: state.spawnedKeys.includes(id) ? state.spawnedKeys : [...state.spawnedKeys, id],
    })),
}))
