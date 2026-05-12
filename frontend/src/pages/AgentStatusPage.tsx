import { useState, useRef, useEffect } from 'react'
import { OfficeMap } from '@/components/office/OfficeMap'
import { useAgentVisualizationStore } from '@/store/useAgentVisualizationStore'
import { getCommandUsage } from '@/apis/aiCommandUsage'
import type { CommandUsageSummary } from '@/apis/aiCommandUsage'
import type {
  AgentConfig,
  AgentRuntime,
  Destination,
  UIDestination,
  SittingState,
  AgentVisualizationInfo,
  AgentActivityStatus,
  TaskStatus,
} from '@/components/office/types'
import { useVisualizationSync } from '@/hooks/useVisualizationSync'
import { useAgentInfoSync } from '@/hooks/useAgentInfoSync'

const ACTIVITY_STATUS_LABEL: Record<AgentActivityStatus, string> = {
  spawning: '진입 중',
  working: '작업 중',
  resting: '휴식 중',
  inactive: '비활성',
}

const ACTIVITY_STATUS_CLASS: Record<AgentActivityStatus, string> = {
  spawning: 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30',
  working: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  resting: 'bg-green-500/20 text-green-300 border border-green-500/30',
  inactive: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
}

const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  pending: '대기 중',
  in_progress: '진행 중',
  completed: '완료',
  failed: '실패',
}

const TASK_STATUS_CLASS: Record<TaskStatus, string> = {
  pending: 'text-yellow-300',
  in_progress: 'text-blue-300',
  completed: 'text-green-300',
  failed: 'text-red-400',
}

function AgentInfoPanel({ info, onClose }: { info: AgentVisualizationInfo; onClose: () => void }) {
  return (
    <div className="absolute top-4 right-4 z-30 flex w-72 flex-col rounded-2xl border border-white/15 bg-black/80 shadow-2xl backdrop-blur-md">
      {/* 헤더 */}
      <div className="flex items-start justify-between border-b border-white/10 p-4">
        <div className="flex items-center gap-3">
          {info.profileImage ? (
            <img
              src={info.profileImage}
              alt={info.name}
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-500/30 text-sm font-bold text-white">
              {info.name[0]}
            </div>
          )}
          <div>
            <p className="text-sm font-semibold text-white">{info.name}</p>
            <p className="text-xs text-white/50">{info.role}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-lg leading-none text-white/30 transition-colors hover:text-white"
        >
          ×
        </button>
      </div>

      {/* 활동 상태 */}
      <div className="border-b border-white/10 px-4 py-2.5">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${ACTIVITY_STATUS_CLASS[info.activityStatus]}`}
        >
          {ACTIVITY_STATUS_LABEL[info.activityStatus]}
        </span>
      </div>

      {/* 현재 작업 */}
      {info.currentTask && (
        <div className="border-b border-white/10 px-4 py-3">
          <p className="mb-1.5 text-xs tracking-wide text-white/35 uppercase">현재 작업</p>
          <p className="text-sm font-semibold text-white">{info.currentTask.title}</p>
          {info.currentTask.description && (
            <p className="mt-1 line-clamp-2 text-xs text-white/50">
              {info.currentTask.description}
            </p>
          )}
          <span
            className={`mt-1.5 inline-block text-xs ${TASK_STATUS_CLASS[info.currentTask.status]}`}
          >
            ● {TASK_STATUS_LABEL[info.currentTask.status]}
          </span>
        </div>
      )}

      {/* 스킬 */}
      <div className="border-b border-white/10 px-4 py-3">
        <p className="mb-1.5 text-xs tracking-wide text-white/35 uppercase">스킬</p>
        <div className="flex flex-wrap gap-1">
          {info.skills.map((skill) => (
            <span key={skill} className="rounded-md bg-white/10 px-2 py-0.5 text-xs text-white/70">
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* 작업 내역 */}
      <div className="max-h-48 flex-1 overflow-y-auto px-4 py-3">
        <p className="mb-2 text-xs tracking-wide text-white/35 uppercase">작업 내역</p>
        {info.taskHistory.length === 0 ? (
          <p className="text-xs text-white/30">작업 내역 없음</p>
        ) : (
          <div className="space-y-2">
            {info.taskHistory.map((task) => (
              <div key={task.taskId} className="flex items-start gap-2">
                <span className="mt-0.5 shrink-0 text-xs text-green-400">✓</span>
                <div>
                  <p className="text-xs text-white/80">{task.title}</p>
                  {task.completedAt && (
                    <p className="text-xs text-white/30">
                      {new Date(task.completedAt).toLocaleDateString('ko-KR')}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 편집 버튼 — 추후 편집 모달 연결 */}
      <div className="border-t border-white/10 px-4 py-3">
        <button className="w-full rounded-lg bg-white/10 py-1.5 text-xs font-medium text-white transition-colors hover:bg-white/20">
          에이전트 편집
        </button>
      </div>
    </div>
  )
}

// 새 에이전트 추가 시 이 배열에 항목만 추가하면 됩니다.
const AGENT_CONFIGS: AgentConfig[] = [
  {
    id: 'agent01',
    name: 'Agent 01',
    spritePath: '/assets/agents/agent01',
    stateScales: { sitting_meeting: 0.85, sitting_calling: 0.85, sitting_floor_lean: 0.85 },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 470, y: 395 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1545, y: 285 },
      meeting: { x: 415, y: 130 },
      calling: { x: 1110, y: 660 },
      work: { x: 470, y: 395 },
    },
  },
  {
    id: 'agent02',
    name: 'Agent 02',
    spritePath: '/assets/agents/agent02',
    stateScales: { sitting_meeting: 0.85, sitting_floor_lean: 0.85, sitting_calling: 0.85 },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 650, y: 458 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1070, y: 285 },
      meeting: { x: 925, y: 90 },
      calling: { x: 840, y: 350 },
      work: { x: 650, y: 458 },
    },
  },
  {
    id: 'agent03',
    name: 'Agent 03',
    spritePath: '/assets/agents/agent03',
    scale: 0.85,
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 470, y: 395 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1215, y: 370 },
      meeting: { x: 715, y: 215 },
      calling: { x: 990, y: 750 },
      work: { x: 470, y: 395 },
    },
  },
  {
    id: 'agent04',
    name: 'Agent 04',
    spritePath: '/assets/agents/agent04',
    scale: 0.87,
    stateScales: { sitting_desk: 1.1, sitting_floor_lean: 0.85 },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 465, y: 595 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1415, y: 360 },
      meeting: { x: 920, y: 220 },
      calling: { x: 1110, y: 655 },
      work: { x: 465, y: 595 },
    },
  },
  {
    id: 'agent05',
    name: 'Agent 05',
    spritePath: '/assets/agents/agent05',
    stateScales: {
      sitting_desk: 0.92,
      sitting_meeting: 0.85,
      sitting_floor_lean: 0.8,
      sitting_calling: 0.9,
    },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 825, y: 520 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1535, y: 425 },
      meeting: { x: 415, y: 130 },
      calling: { x: 1334, y: 665 },
      work: { x: 825, y: 520 },
    },
  },
  {
    id: 'agent06',
    name: 'Agent 06',
    spritePath: '/assets/agents/agent06',
    stateScales: {
      sitting_floor_lean: 0.85,
      sitting_meeting: 0.85,
      sitting_calling: 0.85,
      sitting_sofa: 0.85,
    },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 825, y: 520 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1290, y: 260 },
      meeting: { x: 925, y: 90 },
      calling: { x: 1070, y: 658 },
      work: { x: 825, y: 520 },
    },
  },
  {
    id: 'agent07',
    name: 'Agent 07',
    spritePath: '/assets/agents/agent07',
    stateScales: {
      sitting_meeting: 0.8,
      sitting_sofa: 0.85,
      sitting_floor_lean: 0.85,
      sitting_calling: 0.85,
    },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 465, y: 595 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1340, y: 280 },
      meeting: { x: 850, y: 75 },
      calling: { x: 1430, y: 840 },
      work: { x: 465, y: 595 },
    },
  },
  {
    id: 'agent08',
    name: 'Agent 08',
    spritePath: '/assets/agents/agent08',
    scale: 0.85,
    stateScales: { sitting_sofa: 1.1, sitting_desk: 0.95, sitting_calling: 1.1 },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 650, y: 458 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 995, y: 340 },
      meeting: { x: 670, y: 105 },
      calling: { x: 240, y: 710 },
      work: { x: 650, y: 458 },
    },
  },
  {
    id: 'agent09',
    name: 'Agent 09',
    spritePath: '/assets/agents/agent09',
    scale: 0.85,
    stateScales: { sitting_desk: 1.1 },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 650, y: 685 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1380, y: 490 },
      meeting: { x: 785, y: 245 },
      calling: { x: 1200, y: 658 },
      work: { x: 650, y: 685 },
    },
  },
  {
    id: 'agent10',
    name: 'Agent 10',
    spritePath: '/assets/agents/agent10',
    scale: 0.85,
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 650, y: 685 },
      sofa: { x: 1185, y: 205 },
      floorLean: { x: 1310, y: 460 },
      meeting: { x: 920, y: 220 },
      calling: { x: 1250, y: 660 },
      work: { x: 650, y: 685 },
    },
  },
  {
    id: 'ceo',
    name: 'CEO',
    spritePath: '/assets/agents/ceo',
    scale: 1.05,
    stateScales: { walking: 0.85, standing_wait: 0.85, sitting_work: 0.7 },
    sittingSprites: {
      sitting_desk: 'ceo_desk',
      sitting_meeting: 'ceo_explain',
      sitting_work: 'ceo_work',
      standing_wait: 'walk_side_stand',
    },
    allowedUIDestinations: ['desk', 'meeting', 'work'],
    destinationLabels: { meeting: '화이트보드', work: '작업' },
    initialPosition: { x: 1460, y: 700 },
    destinations: {
      desk: { x: 310, y: 215 },
      meeting: { x: 383, y: 493 },
      work: { x: 275, y: 195 },
      sofa: { x: 310, y: 215 },
      floorLean: { x: 310, y: 215 },
      calling: { x: 310, y: 215 },
    },
  },
]

// ── 격자 A* 경로탐색 ─────────────────────────────────────────────────────────
// OBSTACLE_RECTS에 장애물 사각형(맵 픽셀 좌표)을 추가하면 에이전트가 자동으로 피해서 이동합니다.
// 좌표 확인은 맵 클릭 시 나타나는 노란색 디버그 좌표를 활용하세요.
const CELL = 32 // 격자 셀 크기(px) — 32 → 맵을 50×29 격자로 분할
const GRID_W = Math.ceil(1600 / CELL) // 50
const GRID_H = Math.ceil(900 / CELL) // 29
// 에이전트 스프라이트 중심 기준으로 발 위치까지의 오프셋 — 장애물 충돌을 발 기준으로 판정
const FOOT_OFFSET_Y = 70
const NAVMESH_SRC = '/assets/maps/navmesh.png'
const WALKABLE_THRESHOLD = 128

// 두 점 사이의 직선을 격자 셀로 래스터화 (Bresenham's line)
function rasterizeLine(
  x0: number,
  y0: number,
  x1: number,
  y1: number,
): { gx: number; gy: number }[] {
  let gx0 = Math.floor(x0 / CELL),
    gy0 = Math.floor(y0 / CELL)
  const gx1 = Math.floor(x1 / CELL),
    gy1 = Math.floor(y1 / CELL)
  const cells: { gx: number; gy: number }[] = []
  const dx = Math.abs(gx1 - gx0),
    dy = Math.abs(gy1 - gy0)
  const sx = gx0 < gx1 ? 1 : -1,
    sy = gy0 < gy1 ? 1 : -1
  let err = dx - dy
  for (;;) {
    cells.push({ gx: gx0, gy: gy0 })
    if (gx0 === gx1 && gy0 === gy1) break
    const e2 = 2 * err
    if (e2 > -dy) {
      err -= dy
      gx0 += sx
    }
    if (e2 < dx) {
      err += dx
      gy0 += sy
    }
  }
  return cells
}

// 책상 장애물 — 목적지가 'desk'일 때는 통과 허용
const DESK_OBSTACLE_RECTS = [
  { x1: 439, y1: 320, x2: 601, y2: 459 },
  { x1: 628, y1: 380, x2: 781, y2: 522 },
  { x1: 808, y1: 451, x2: 961, y2: 602 },
  { x1: 446, y1: 531, x2: 599, y2: 677 },
  { x1: 629, y1: 607, x2: 781, y2: 728 },
]

// 소파·벽 외곽 폴리곤 — 목적지가 'sofa' 또는 'floorLean'일 때는 통과 허용
const SOFA_WALL_OBSTACLE_LINES = [
  { x1: 899, y1: 307, x2: 899, y2: 376 },
  { x1: 1167, y1: 114, x2: 901, y2: 309 },
  { x1: 897, y1: 379, x2: 926, y2: 390 },
  { x1: 928, y1: 390, x2: 1062, y2: 284 },
  { x1: 1062, y1: 284, x2: 1126, y2: 310 },
  { x1: 1127, y1: 307, x2: 1280, y2: 183 },
  { x1: 1280, y1: 179, x2: 1166, y2: 114 },
]

// 테이블 외곽 폴리곤 — 항상 통행 불가
const TABLE_OBSTACLE_LINES = [
  { x1: 742, y1: 89, x2: 673, y2: 139 },
  { x1: 674, y1: 136, x2: 674, y2: 211 },
  { x1: 674, y1: 211, x2: 844, y2: 278 },
  { x1: 841, y1: 276, x2: 916, y2: 220 },
  { x1: 916, y1: 218, x2: 916, y2: 157 },
  { x1: 743, y1: 85, x2: 917, y2: 153 },
]

// 장애물 사각형 목록
const OBSTACLE_RECTS: { x1: number; y1: number; x2: number; y2: number }[] = [
  ...DESK_OBSTACLE_RECTS,
  { x1: 77, y1: 351, x2: 379, y2: 579 }, // 왼쪽 벽
  { x1: 1415, y1: 467, x2: 1559, y2: 703 }, // 엘리베이터
]

const OBSTACLE_GRID: boolean[][] = (() => {
  const g: boolean[][] = Array.from({ length: GRID_H }, () => Array(GRID_W).fill(false))
  for (const r of OBSTACLE_RECTS)
    for (let gy = Math.floor(r.y1 / CELL); gy <= Math.floor(r.y2 / CELL); gy++)
      for (let gx = Math.floor(r.x1 / CELL); gx <= Math.floor(r.x2 / CELL); gx++)
        if (gy >= 0 && gy < GRID_H && gx >= 0 && gx < GRID_W) g[gy][gx] = true
  for (const l of [...SOFA_WALL_OBSTACLE_LINES, ...TABLE_OBSTACLE_LINES])
    for (const cell of rasterizeLine(l.x1, l.y1, l.x2, l.y2))
      if (cell.gy >= 0 && cell.gy < GRID_H && cell.gx >= 0 && cell.gx < GRID_W)
        g[cell.gy][cell.gx] = true
  return g
})()

function imageToObstacleGrid(img: HTMLImageElement): boolean[][] {
  const canvas = document.createElement('canvas')
  canvas.width = 1600
  canvas.height = 900

  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return OBSTACLE_GRID

  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  const grid: boolean[][] = Array.from({ length: GRID_H }, () => Array(GRID_W).fill(true))
  const sampleOffsets = [
    [0.5, 0.5],
    [0.25, 0.25],
    [0.75, 0.25],
    [0.25, 0.75],
    [0.75, 0.75],
  ] as const

  for (let gy = 0; gy < GRID_H; gy++) {
    for (let gx = 0; gx < GRID_W; gx++) {
      let walkableSamples = 0

      for (const [ox, oy] of sampleOffsets) {
        const px = Math.min(canvas.width - 1, Math.round((gx + ox) * CELL))
        const py = Math.min(canvas.height - 1, Math.round((gy + oy) * CELL))
        const [r, g, b, a] = ctx.getImageData(px, py, 1, 1).data
        const brightness = (r + g + b) / 3
        if (a > 0 && brightness >= WALKABLE_THRESHOLD) walkableSamples++
      }

      grid[gy][gx] = walkableSamples < 3
    }
  }

  return grid
}

function isWalkableCell(grid: boolean[][], gx: number, gy: number): boolean {
  return gy >= 0 && gy < GRID_H && gx >= 0 && gx < GRID_W && !grid[gy][gx]
}

function findNearestWalkableCell(
  grid: boolean[][],
  gx: number,
  gy: number,
): { x: number; y: number } {
  if (isWalkableCell(grid, gx, gy)) return { x: gx, y: gy }

  for (let radius = 1; radius < Math.max(GRID_W, GRID_H); radius++) {
    let best: { x: number; y: number; dist: number } | null = null

    for (let y = gy - radius; y <= gy + radius; y++) {
      for (let x = gx - radius; x <= gx + radius; x++) {
        if (Math.abs(x - gx) !== radius && Math.abs(y - gy) !== radius) continue
        if (!isWalkableCell(grid, x, y)) continue

        const dist = (x - gx) * (x - gx) + (y - gy) * (y - gy)
        if (!best || dist < best.dist) best = { x, y, dist }
      }
    }

    if (best) return { x: best.x, y: best.y }
  }

  return { x: gx, y: gy }
}

function cellToMapPoint(cell: { x: number; y: number }): { x: number; y: number } {
  return {
    x: cell.x * CELL + CELL / 2,
    y: cell.y * CELL + CELL / 2 - FOOT_OFFSET_Y,
  }
}

function samePoint(a: { x: number; y: number }, b: { x: number; y: number }): boolean {
  return Math.abs(a.x - b.x) < 1 && Math.abs(a.y - b.y) < 1
}

function canWalkStraight(
  from: { x: number; y: number },
  to: { x: number; y: number },
  grid: boolean[][],
): boolean {
  const cells = rasterizeLine(from.x, from.y + FOOT_OFFSET_Y, to.x, to.y + FOOT_OFFSET_Y)
  return cells.every(({ gx, gy }) => isWalkableCell(grid, gx, gy))
}

function smoothPath(
  pts: { x: number; y: number }[],
  grid: boolean[][],
  from: { x: number; y: number },
  to: { x: number; y: number },
): { x: number; y: number }[] {
  const route = [from, ...pts, to]
  const out: { x: number; y: number }[] = []
  let anchor = 0

  while (anchor < route.length - 1) {
    let next = route.length - 1
    while (next > anchor + 1 && !canWalkStraight(route[anchor], route[next], grid)) next--
    out.push(route[next])
    anchor = next
  }

  return out
}

function findPath(
  from: { x: number; y: number },
  to: { x: number; y: number },
  passableRects?: { x1: number; y1: number; x2: number; y2: number }[],
  baseGrid?: boolean[][],
  passableLines?: { x1: number; y1: number; x2: number; y2: number }[],
): { x: number; y: number }[] {
  const sx = Math.floor(from.x / CELL)
  const sy = Math.floor((from.y + FOOT_OFFSET_Y) / CELL)
  const ex = Math.floor(to.x / CELL)
  const ey = Math.floor((to.y + FOOT_OFFSET_Y) / CELL)
  const baseG = baseGrid ?? OBSTACLE_GRID
  const grid = baseG.map((r) => [...r])

  // 목적지 셀은 항상 통과 가능 — navmesh에서 목적지가 장애물 내부여도 도달 가능

  if (passableRects?.length) {
    for (const r of passableRects)
      for (let gy = Math.floor(r.y1 / CELL); gy <= Math.floor(r.y2 / CELL); gy++)
        for (let gx = Math.floor(r.x1 / CELL); gx <= Math.floor(r.x2 / CELL); gx++)
          if (gy >= 0 && gy < GRID_H && gx >= 0 && gx < GRID_W) grid[gy][gx] = false
  }
  if (passableLines?.length) {
    for (const l of passableLines)
      for (const cell of rasterizeLine(l.x1, l.y1, l.x2, l.y2))
        if (cell.gy >= 0 && cell.gy < GRID_H && cell.gx >= 0 && cell.gx < GRID_W)
          grid[cell.gy][cell.gx] = false
  }

  const start = findNearestWalkableCell(grid, sx, sy)
  const end = findNearestWalkableCell(grid, ex, ey)
  const pathTarget = cellToMapPoint(end)
  if (start.x === end.x && start.y === end.y) return samePoint(pathTarget, to) ? [] : [pathTarget]

  type N = { x: number; y: number; g: number; h: number; prev: N | null }
  const key = (x: number, y: number) => y * GRID_W + x
  const open = new Map<number, N>()
  const closed = new Set<number>()
  open.set(key(start.x, start.y), {
    x: start.x,
    y: start.y,
    g: 0,
    h: Math.hypot(start.x - end.x, start.y - end.y),
    prev: null,
  })

  const DIRS = [
    [0, 1],
    [0, -1],
    [1, 0],
    [-1, 0],
    [1, 1],
    [1, -1],
    [-1, 1],
    [-1, -1],
  ]
  const COST = [1, 1, 1, 1, 1.41, 1.41, 1.41, 1.41]

  let iters = 0
  while (open.size > 0 && iters++ < 10000) {
    let cur: N | null = null
    for (const n of open.values()) if (!cur || n.g + n.h < cur.g + cur.h) cur = n
    if (!cur) break
    open.delete(key(cur.x, cur.y))
    closed.add(key(cur.x, cur.y))

    if (cur.x === end.x && cur.y === end.y) {
      const pts: { x: number; y: number }[] = []
      // cur(목적지 셀 중심)는 제외 — allStops에서 실제 목적지 좌표가 추가되므로 여분 걸음 방지
      let n: N | null = cur.prev
      while (n?.prev) {
        pts.push({ x: n.x * CELL + CELL / 2, y: n.y * CELL + CELL / 2 - FOOT_OFFSET_Y })
        n = n.prev
      }
      return smoothPath(pts.reverse(), grid, from, pathTarget)
    }

    for (let d = 0; d < 8; d++) {
      const nx = cur.x + DIRS[d][0]
      const ny = cur.y + DIRS[d][1]
      if (nx < 0 || nx >= GRID_W || ny < 0 || ny >= GRID_H) continue
      if (grid[ny][nx]) continue
      if (DIRS[d][0] !== 0 && DIRS[d][1] !== 0 && (grid[cur.y][nx] || grid[ny][cur.x])) continue
      const k = key(nx, ny)
      if (closed.has(k)) continue
      const ng = cur.g + COST[d]
      const existing = open.get(k)
      if (!existing || ng < existing.g) {
        const dx1 = nx - end.x
        const dy1 = ny - end.y
        // 타이브레이킹: 시작→목적지 직선 방향에 가까운 경로를 우선 선택해 지그재그 억제
        const cross = Math.abs(dx1 * (start.y - end.y) - (start.x - end.x) * dy1)
        open.set(k, { x: nx, y: ny, g: ng, h: Math.hypot(dx1, dy1) + cross * 0.001, prev: cur })
      }
    }
  }
  return []
}

const WALK_SPEED = 100
const FRAME_DURATIONS = [300, 120, 300, 120] as const
const AGENT_BLOCK_RADIUS_CELLS = 1
const AGENT_COLLISION_RADIUS = 90
const SPOT_OCCUPIED_RADIUS = 40 // 자리 점유 판정 반경 (소파 두 자리 간격 ~51px보다 작아야 함)

// 책상 대기 줄 — 책상이 점유 중일 때 (880, 640)부터 순서대로 80px 간격으로 줄서기
const DESK_WAIT_QUEUE: { x: number; y: number }[] = Array.from({ length: 10 }, (_, i) => ({
  x: 880 + i * 80,
  y: 640,
}))

// 맵 상의 소파 자리 2곳 — 휴식 버튼 클릭 시 빈 자리부터 배정
const SOFA_SPOTS: { x: number; y: number }[] = [
  { x: 1185, y: 205 },
  { x: 1140, y: 230 },
]

const DESTINATION_MAP: Record<UIDestination, { targetState: SittingState; label: string }> = {
  desk: { targetState: 'sitting_desk', label: '책상' },
  rest: { targetState: 'sitting_sofa', label: '휴식' }, // 런타임에 sofa/floorLean 으로 오버라이드
  meeting: { targetState: 'sitting_meeting', label: '회의' },
  calling: { targetState: 'sitting_calling', label: '전화' },
  work: { targetState: 'sitting_work', label: '작업' },
}

const STATE_LABELS: Record<string, string> = {
  idle: '대기 중',
  walking: '이동 중',
  sitting_desk: '작업 중',
  sitting_sofa: '휴식 중',
  sitting_floor_lean: '휴식 중',
  sitting_meeting: '회의 중',
  sitting_calling: '통화 중',
  sitting_work: '작업 중',
  standing_wait: '대기 중',
}

function stateColor(state: string) {
  if (state === 'sitting_calling') return 'bg-blue-400'
  if (state.startsWith('sitting')) return 'bg-green-400'
  if (state === 'walking') return 'bg-yellow-400'
  if (state === 'standing_wait') return 'bg-orange-400'
  return 'bg-slate-500'
}

function calcDuration(from: { x: number; y: number }, to: { x: number; y: number }): number {
  const dx = to.x - from.x
  const dy = to.y - from.y
  return Math.max(1, Math.sqrt(dx * dx + dy * dy) / WALK_SPEED)
}

function pointToFootCell(point: { x: number; y: number }): { x: number; y: number } {
  return {
    x: Math.floor(point.x / CELL),
    y: Math.floor((point.y + FOOT_OFFSET_Y) / CELL),
  }
}

function withAgentBlockers(
  baseGrid: boolean[][],
  agents: AgentRuntime[],
  movingAgentId: string,
): boolean[][] {
  const grid = baseGrid.map((row) => [...row])

  for (const agent of agents) {
    if (agent.config.id === movingAgentId) continue

    const foot = pointToFootCell(agent.position)
    for (
      let gy = foot.y - AGENT_BLOCK_RADIUS_CELLS;
      gy <= foot.y + AGENT_BLOCK_RADIUS_CELLS;
      gy++
    ) {
      for (
        let gx = foot.x - AGENT_BLOCK_RADIUS_CELLS;
        gx <= foot.x + AGENT_BLOCK_RADIUS_CELLS;
        gx++
      ) {
        if (gy >= 0 && gy < GRID_H && gx >= 0 && gx < GRID_W) grid[gy][gx] = true
      }
    }
  }

  return grid
}

function isOccupiedByAnotherAgent(
  point: { x: number; y: number },
  agents: AgentRuntime[],
  movingAgentId: string,
): boolean {
  return agents.some((agent) => {
    if (agent.config.id === movingAgentId) return false
    return (
      Math.hypot(agent.position.x - point.x, agent.position.y - point.y) < AGENT_COLLISION_RADIUS
    )
  })
}

// 해당 자리가 점유 중인지 확인
// — 이미 정착한 에이전트 OR 동일 자리를 향해 이동 중인 에이전트 모두 점유로 간주
function isSpotOccupied(
  spot: { x: number; y: number },
  agents: AgentRuntime[],
  excludeId: string,
): boolean {
  return agents.some((a) => {
    if (a.config.id === excludeId) return false
    // 정착(앉거나 대기) 에이전트
    if (
      a.state !== 'idle' &&
      a.state !== 'walking' &&
      Math.hypot(a.position.x - spot.x, a.position.y - spot.y) < SPOT_OCCUPIED_RADIUS
    )
      return true
    // 동시에 같은 자리로 이동 중인 에이전트 — 중복 배정 방지
    if (
      a.state === 'walking' &&
      a.targetPosition != null &&
      Math.hypot(a.targetPosition.x - spot.x, a.targetPosition.y - spot.y) < SPOT_OCCUPIED_RADIUS
    )
      return true
    return false
  })
}

const DESTINATIONS: UIDestination[] = ['desk', 'rest', 'meeting', 'calling']

function playSpawnSound() {
  try {
    const ctx = new AudioContext()
    const play = () => {
      ;[1318.51, 1567.98].forEach((freq, i) => {
        const osc = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.type = 'sine'
        osc.frequency.value = freq
        const t = ctx.currentTime + i * 0.12
        gain.gain.setValueAtTime(0.18, t)
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.45)
        osc.start(t)
        osc.stop(t + 0.45)
      })
    }
    // 페이지 내 이동으로 진입한 경우 AudioContext가 이미 running 상태이므로 즉시 재생됨
    // 직접 URL 접근 시 브라우저가 차단하면 소리 없이 무시
    void ctx.resume().then(play)
  } catch {
    // AudioContext 미지원 환경 무시
  }
}

export function AgentStatusPage() {
  const [agents, setAgents] = useState<AgentRuntime[]>([])
  const [selectedId, setSelectedId] = useState('agent01')
  const [panelTop, setPanelTop] = useState(false)
  const [navmeshGrid, setNavmeshGrid] = useState<boolean[][] | null>(null)
  const [spawningIds, setSpawningIds] = useState<ReadonlySet<string>>(new Set())
  const [tokenUsageSummary, setTokenUsageSummary] = useState<CommandUsageSummary | null>(null)

  useEffect(() => {
    void getCommandUsage({})
      .then((d) => setTokenUsageSummary(d.summary))
      .catch(() => {
        // 임시 mock — API 연동 전 화이트보드 차트 미리보기용
        setTokenUsageSummary({
          inputTokens: 8400,
          outputTokens: 3200,
          cachedInputTokens: 1500,
          reasoningTokens: 900,
          totalTokens: 11600,
          estimatedCostUsd: 0.0842,
          currency: 'USD',
          recordCount: 47,
        })
      })
  }, [])
  const runtimeGridRef = useRef<boolean[][]>(OBSTACLE_GRID)
  const walkTimersRef = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({})

  const { agentInfoMap, selectedAgentId, selectAgent } = useAgentVisualizationStore()
  const spawnedKeysRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    const img = new Image()

    img.onload = () => {
      if (!cancelled) setNavmeshGrid(imageToObstacleGrid(img))
    }
    img.onerror = () => {
      if (!cancelled) setNavmeshGrid(null)
    }
    img.src = NAVMESH_SRC

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    runtimeGridRef.current = (navmeshGrid ?? OBSTACLE_GRID).map((r) => [...r])
  }, [navmeshGrid])

  const clearWalkTimer = (agentId: string) => {
    const timer = walkTimersRef.current[agentId]
    if (timer !== undefined) {
      clearTimeout(timer)
      delete walkTimersRef.current[agentId]
    }
  }

  const handleMove = (agentId: string, destination: UIDestination) => {
    // 미등록 에이전트 자동 스폰 — task run에서 처음 등장하는 경우
    if (!spawnedKeysRef.current.has(agentId) && AGENT_CONFIGS.some((c) => c.id === agentId)) {
      spawnedKeysRef.current.add(agentId)
      setSpawningIds((s) => new Set([...s, agentId]))
      playSpawnSound()
      setTimeout(() => {
        setSpawningIds((s) => {
          const n = new Set(s)
          n.delete(agentId)
          return n
        })
      }, 2500)
    }

    setAgents((prevAgents) => {
      // 아직 agents 배열에 없으면 initialPosition에 추가
      let prev = prevAgents
      if (!prev.some((a) => a.config.id === agentId)) {
        const config = AGENT_CONFIGS.find((c) => c.id === agentId)
        if (!config) return prev
        prev = [
          ...prev,
          {
            config,
            position: { ...config.initialPosition },
            state: 'idle' as const,
            targetState: 'sitting_desk' as const,
            walkFrame: 0 as const,
            transitionDuration: 3,
            pendingWaypoints: [],
            targetPosition: null,
            standWaitTarget: null,
            facingRight: false,
          },
        ]
      }

      const agent = prev.find((a) => a.config.id === agentId)
      if (!agent || agent.state === 'walking') return prev

      // ── rest → 소파 빈 자리 우선 배정, 둘 다 차면 floorLean ──────────────
      let internalDest: Destination
      let destPoint: { x: number; y: number }
      if (destination === 'rest') {
        const freeSofaSpot = SOFA_SPOTS.find((spot) => !isSpotOccupied(spot, prev, agentId))
        if (freeSofaSpot) {
          internalDest = 'sofa'
          destPoint = { ...freeSofaSpot }
        } else {
          internalDest = 'floorLean'
          destPoint = { ...agent.config.destinations.floorLean }
        }
      } else {
        internalDest = destination
        destPoint = { ...agent.config.destinations[internalDest] }

        // 책상 자리가 점유된 경우 대기 줄 대신 회의 목적지로 바로 전환
        if (internalDest === 'desk' && isSpotOccupied(destPoint, prev, agentId)) {
          internalDest = 'meeting'
          destPoint = { ...agent.config.destinations.meeting }
        }
      }

      const destConfig = agent.config.destinations[internalDest]

      // internalDest 에 맞는 실제 앉기 상태
      const resolvedTargetState: SittingState =
        internalDest === 'sofa'
          ? 'sitting_sofa'
          : internalDest === 'floorLean'
            ? 'sitting_floor_lean'
            : DESTINATION_MAP[internalDest as UIDestination].targetState

      // 목적지 자리가 이미 점유 중이면 옆에 서 있는 상태로 전환
      const targetState: SittingState = isSpotOccupied(destPoint, prev, agentId)
        ? 'standing_wait'
        : resolvedTargetState

      const passableRects =
        !navmeshGrid && internalDest === 'desk' ? DESK_OBSTACLE_RECTS : undefined
      const passableLines =
        !navmeshGrid && (internalDest === 'sofa' || internalDest === 'floorLean')
          ? SOFA_WALL_OBSTACLE_LINES
          : undefined

      const pathGrid = withAgentBlockers(runtimeGridRef.current, prev, agentId)

      // standing_wait: 책상이 차 있으면 고정 대기 줄에 순서대로 배정
      let standWaitOrigin: { x: number; y: number } | null = null
      if (targetState === 'standing_wait') {
        standWaitOrigin = { ...destPoint }
        const freeSlot =
          DESK_WAIT_QUEUE.find((spot) => !isSpotOccupied(spot, prev, agentId)) ??
          DESK_WAIT_QUEUE[DESK_WAIT_QUEUE.length - 1]
        destPoint = { ...freeSlot }
      }

      // rest·standing_wait 는 커스텀 waypoints 미사용
      const waypoints =
        (destination !== 'rest' && targetState !== 'standing_wait'
          ? destConfig.waypoints
          : undefined) ??
        findPath(agent.position, destPoint, passableRects, pathGrid, passableLines)

      const lastStop = waypoints[waypoints.length - 1]
      // 소파는 SOFA_SPOTS의 고정 좌표를 항상 사용 — isOccupiedByAnotherAgent 반경(90px)이 소파 두 자리 간격(~51px)보다 커서 좌표가 셀 중심으로 벗어나는 문제 방지
      const finalPosition =
        internalDest !== 'sofa' && lastStop && isOccupiedByAnotherAgent(destPoint, prev, agentId)
          ? lastStop
          : destPoint
      const allStops = waypoints
      const firstStop = allStops[0]
      if (!firstStop) {
        clearWalkTimer(agentId)
        // standing_wait 즉시 배치 시 점유된 자리 방향으로 바라봄
        const arrivalFacing = standWaitOrigin
          ? Math.abs(standWaitOrigin.x - finalPosition.x) > 5
            ? standWaitOrigin.x > finalPosition.x
            : agent.facingRight
          : agent.facingRight
        return prev.map((a) =>
          a.config.id === agentId
            ? {
                ...a,
                position: { ...finalPosition },
                state: targetState,
                targetState,
                walkFrame: 0,
                pendingWaypoints: [],
                targetPosition: null,
                standWaitTarget: standWaitOrigin,
                facingRight: arrivalFacing,
              }
            : a,
        )
      }
      const remaining = allStops.slice(1)
      // 최종 목적지 방향으로 facing 결정 — 웨이포인트마다 좌우 반전 방지
      const overallDx = finalPosition.x - agent.position.x
      const facingRight = Math.abs(overallDx) > CELL ? overallDx > 0 : agent.facingRight

      clearWalkTimer(agentId)

      const scheduleWalkStep = (frame: 0 | 1 | 2 | 3) => {
        walkTimersRef.current[agentId] = setTimeout(() => {
          const next = ((frame + 1) % 4) as 0 | 1 | 2 | 3
          setAgents((p) => p.map((a) => (a.config.id === agentId ? { ...a, walkFrame: next } : a)))
          scheduleWalkStep(next)
        }, FRAME_DURATIONS[frame])
      }
      scheduleWalkStep(0)

      return prev.map((a) =>
        a.config.id === agentId
          ? {
              ...a,
              state: 'walking' as const,
              targetState,
              position: { ...firstStop },
              transitionDuration: calcDuration(agent.position, firstStop),
              pendingWaypoints: remaining,
              targetPosition: { ...finalPosition },
              // standing_wait 도착 시 점유된 자리 방향을 바라보기 위해 원본 좌표 저장
              standWaitTarget: standWaitOrigin,
              facingRight,
            }
          : a,
      )
    })
  }

  useVisualizationSync(handleMove)
  useAgentInfoSync()

  const handleAgentArrived = (agentId: string) => {
    setAgents((prev) => {
      const agent = prev.find((a) => a.config.id === agentId)
      if (!agent) return prev

      if (agent.pendingWaypoints.length > 0) {
        const [next, ...rest] = agent.pendingWaypoints
        // 최종 목적지 방향 기준으로 facing 유지 — 경유 웨이포인트 방향에 흔들리지 않도록
        const finalTarget = agent.targetPosition ?? next
        const overallDx = finalTarget.x - agent.position.x
        const facingRight = Math.abs(overallDx) > CELL ? overallDx > 0 : agent.facingRight
        return prev.map((a) =>
          a.config.id === agentId
            ? {
                ...a,
                position: { ...next },
                transitionDuration: calcDuration(a.position, next),
                pendingWaypoints: rest,
                facingRight,
              }
            : a,
        )
      }

      clearWalkTimer(agentId)
      return prev.map((a) => {
        if (a.config.id !== agentId) return a
        // standing_wait 도착 시 저장해둔 목적지 좌표 방향으로 바라봄
        const finalFacing =
          a.targetState === 'standing_wait' && a.standWaitTarget
            ? a.standWaitTarget.x > (a.targetPosition?.x ?? a.position.x)
            : a.facingRight
        return {
          ...a,
          position: a.targetPosition ? { ...a.targetPosition } : a.position,
          state: a.targetState,
          walkFrame: 0,
          pendingWaypoints: [],
          targetPosition: null,
          standWaitTarget: null,
          facingRight: finalFacing,
        }
      })
    })
  }

  const handleReset = (agentId: string) => {
    clearWalkTimer(agentId)
    setAgents((prev) =>
      prev.map((a) =>
        a.config.id === agentId
          ? {
              ...a,
              position: { ...a.config.initialPosition },
              state: 'idle' as const,
              targetState: 'sitting_desk' as const,
              walkFrame: 0 as const,
              pendingWaypoints: [],
              targetPosition: null,
              standWaitTarget: null,
              facingRight: false,
            }
          : a,
      ),
    )
  }

  const selectedAgent = agents.find((a) => a.config.id === selectedId)

  const selectedInfo = selectedAgentId ? agentInfoMap[selectedAgentId] : null

  return (
    <div className="relative flex flex-1 overflow-hidden">
      <OfficeMap
        agents={agents}
        onAgentArrived={handleAgentArrived}
        ceoMode={null}
        onAgentClick={selectAgent}
        agentInfoMap={agentInfoMap}
        selectedAgentId={selectedAgentId}
        spawningIds={spawningIds}
        tokenUsageSummary={tokenUsageSummary}
      />
      {selectedInfo && <AgentInfoPanel info={selectedInfo} onClose={() => selectAgent(null)} />}

      <div className={`absolute left-1/2 z-20 -translate-x-1/2 ${panelTop ? 'top-4' : 'bottom-6'}`}>
        <div className="flex flex-col gap-2.5 rounded-2xl border border-white/20 bg-black/60 px-5 py-3 shadow-2xl backdrop-blur-md">
          {/* 에이전트 탭 */}
          <div className="flex items-center gap-1.5">
            {agents.map((agent) => (
              <button
                key={agent.config.id}
                onClick={() => setSelectedId(agent.config.id)}
                className={`relative rounded-lg px-3 py-1 text-xs font-bold transition-colors ${
                  selectedId === agent.config.id
                    ? 'bg-white text-gray-900'
                    : 'bg-white/10 text-white/60 hover:bg-white/20 hover:text-white'
                }`}
              >
                {agent.config.id.replace('agent', '')}
                <span
                  className={`absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full border border-black/50 ${stateColor(agent.state)} ${agent.state === 'walking' ? 'animate-pulse' : ''}`}
                />
              </button>
            ))}
            <div className="mx-0.5 h-4 w-px bg-white/20" />
            <button
              onClick={() => setPanelTop((prev) => !prev)}
              className="rounded-lg bg-white/10 px-2 py-1 text-xs text-white/60 transition-colors hover:bg-white/20 hover:text-white"
              title="패널 위치 이동"
            >
              {panelTop ? '▼' : '▲'}
            </button>
          </div>

          {/* 선택된 에이전트 이동 */}
          {selectedAgent && (
            <div className="flex items-center gap-3">
              <div className="flex w-20 shrink-0 flex-col">
                <span className="text-sm font-medium text-white">{selectedAgent.config.name}</span>
                <span className="text-xs text-white/50">{STATE_LABELS[selectedAgent.state]}</span>
              </div>
              <div className="flex gap-1.5">
                {(selectedAgent.config.allowedUIDestinations ?? DESTINATIONS).map((dest) => (
                  <button
                    key={dest}
                    onClick={() => handleMove(selectedAgent.config.id, dest)}
                    disabled={selectedAgent.state === 'walking'}
                    className="rounded-lg bg-white/90 px-3 py-1.5 text-xs font-semibold text-gray-900 shadow-sm transition-opacity hover:bg-white disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    {selectedAgent.config.destinationLabels?.[dest] ?? DESTINATION_MAP[dest].label}
                  </button>
                ))}
              </div>
              <button
                onClick={() => handleReset(selectedAgent.config.id)}
                disabled={selectedAgent.state === 'idle'}
                className="rounded-lg border border-white/30 px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-30"
              >
                초기화
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
