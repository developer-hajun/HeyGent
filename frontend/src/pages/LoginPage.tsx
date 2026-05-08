import { useNavigate } from 'react-router'
import { devLogin } from '@/apis/auth'
import { getMyInfo } from '@/apis/users'
import { useAuthStore } from '@/store/useAuthStore'
import { useEffect, useRef, useCallback, useState } from 'react'

const KAKAO_AUTH_URL =
  `https://kauth.kakao.com/oauth/authorize` +
  `?client_id=${import.meta.env.VITE_KAKAO_CLIENT_ID}` +
  `&redirect_uri=${import.meta.env.VITE_KAKAO_REDIRECT_URI}` +
  `&response_type=code`

// ─── 클러스터 정의 ───────────────────────────────────────────

interface ClusterDef {
  id: number
  rx: number
  ry: number
  label: string
  title: string
  desc: string
  keywords?: string
  count: number
  spread: number
  isMain: boolean
  hubR: number
  hubAlpha: number
  hoverDetectR: number
}

// 비대칭 유기적 배치 — 중앙 텍스트와 좌측 상단 로고를 자연스럽게 피하면서
// 화면 가장자리에는 붙지 않는 ring-like system map 구조
const CLUSTER_DEFS: ClusterDef[] = [
  {
    id: 0,
    rx: 0.5,
    ry: 0.2,
    label: 'CORE HUB',
    title: 'CORE HUB',
    desc: '각 기능 에이전트를 연결하고 전체 흐름과 작업 맥락을 조율하는 중심 허브입니다.',
    keywords: 'Agent Orchestration · Context Routing · System Hub',
    count: 50,
    spread: 105,
    isMain: true,
    hubR: 8.5,
    hubAlpha: 1.0,
    hoverDetectR: 0.15,
  },
  {
    id: 1,
    rx: 0.21,
    ry: 0.42,
    label: 'MEMORY',
    title: 'MEMORY',
    desc: '이전 대화와 세션 맥락을 기억하고 이어줍니다.',
    keywords: 'Session Context · Recall · Persistence',
    count: 18,
    spread: 58,
    isMain: false,
    hubR: 4.4,
    hubAlpha: 0.85,
    hoverDetectR: 0.1,
  },
  {
    id: 2,
    rx: 0.79,
    ry: 0.3,
    label: 'PLANNING',
    title: 'PLANNING',
    desc: '일정, 리마인더, 할 일을 정리하고 관리합니다.',
    keywords: 'Schedule · Reminder · Task Management',
    count: 17,
    spread: 56,
    isMain: false,
    hubR: 4.4,
    hubAlpha: 0.85,
    hoverDetectR: 0.1,
  },
  {
    id: 3,
    rx: 0.18,
    ry: 0.72,
    label: 'VOICE',
    title: 'VOICE',
    desc: '음성 명령과 대화를 통해 에이전트를 호출합니다.',
    keywords: 'Speech · Command · Dialogue',
    count: 16,
    spread: 54,
    isMain: false,
    hubR: 4.2,
    hubAlpha: 0.82,
    hoverDetectR: 0.1,
  },
  {
    id: 4,
    rx: 0.83,
    ry: 0.74,
    label: 'HEALTH',
    title: 'HEALTH',
    desc: '수면, 걸음 수, 운동 기록 등 건강 데이터를 분석합니다.',
    keywords: 'Sleep · Activity · Biometrics',
    count: 17,
    spread: 56,
    isMain: false,
    hubR: 4.2,
    hubAlpha: 0.82,
    hoverDetectR: 0.1,
  },
  {
    id: 5,
    rx: 0.4,
    ry: 0.85,
    label: 'SYNC',
    title: 'SYNC',
    desc: '연결된 서비스와 데이터를 실시간으로 동기화합니다.',
    keywords: 'Real-time · Integration · Data Sync',
    count: 14,
    spread: 50,
    isMain: false,
    hubR: 4.0,
    hubAlpha: 0.8,
    hoverDetectR: 0.1,
  },
  {
    id: 6,
    rx: 0.65,
    ry: 0.8,
    label: 'CONTEXT',
    title: 'CONTEXT',
    desc: '현재 작업 흐름과 필요한 정보를 연결합니다.',
    keywords: 'Workflow · Relevance · State Awareness',
    count: 14,
    spread: 50,
    isMain: false,
    hubR: 4.0,
    hubAlpha: 0.8,
    hoverDetectR: 0.1,
  },
]

// ─── Safe zones ──────────────────────────────────────────────
// 카피 영역 — h1+p 텍스트 실측 영역 + 약간의 여백
const COPY_SZ_HW = 195
const COPY_SZ_HH = 95

function inCopySZ(px: number, py: number, W: number, H: number): boolean {
  return Math.abs(px - W * 0.5) < COPY_SZ_HW && Math.abs(py - H * 0.5) < COPY_SZ_HH
}

// 화면 가장자리 soft margin — 노드는 이 거리 안쪽에서 시작
const EDGE_SOFT = 70

// ─── 타입 ────────────────────────────────────────────────────

type NodeTier = 'hub' | 'normal' | 'background'

interface NetNode {
  ox: number
  oy: number
  x: number
  y: number
  vx: number
  vy: number
  r: number
  baseAlpha: number
  tier: NodeTier
  clusterId: number
  phase: number
  // 통합 코어 cluster 내 자리 — 빌드 시 결정 (Stage 1 merge target)
  mergeR: number
  mergeA: number
}

interface Pulse {
  fromIdx: number
  toIdx: number
  t: number
  speed: number
}

function addVelocity(node: NetNode, vx: number, vy: number): void {
  node.vx += vx
  node.vy += vy
}

function advanceNode(node: NetNode, damping: number): void {
  node.vx *= damping
  node.vy *= damping
  node.x += node.vx
  node.y += node.vy
}

function advancePulse(pulse: Pulse, speedMultiplier: number): void {
  pulse.t += pulse.speed * speedMultiplier
  if (pulse.t > 1) pulse.t = 0
}

// ─── 빌드 ────────────────────────────────────────────────────

function makeMergeOffset(tier: NodeTier, isMain: boolean): { mergeR: number; mergeA: number } {
  const mergeA = Math.random() * Math.PI * 2
  let mergeR: number
  if (tier === 'hub') {
    // CORE HUB hub 는 가장 안쪽 / 다른 hub 는 그 다음
    mergeR = isMain ? 6 + Math.random() * 14 : 26 + Math.random() * 22
  } else if (tier === 'normal') {
    mergeR = 42 + Math.random() * 48
  } else {
    mergeR = 75 + Math.random() * 65
  }
  return { mergeR, mergeA }
}

function buildNetwork(W: number, H: number): NetNode[] {
  const nodes: NetNode[] = []

  for (const cl of CLUSTER_DEFS) {
    const cx = cl.rx * W
    const cy = cl.ry * H

    const hm = makeMergeOffset('hub', cl.isMain)
    nodes.push({
      ox: cx,
      oy: cy,
      x: cx,
      y: cy,
      vx: 0,
      vy: 0,
      r: cl.hubR,
      baseAlpha: cl.hubAlpha,
      tier: 'hub',
      clusterId: cl.id,
      phase: Math.random() * Math.PI * 2,
      mergeR: hm.mergeR,
      mergeA: hm.mergeA,
    })

    if (cl.isMain) {
      for (let k = 0; k < 3; k++) {
        const a = (k / 3) * Math.PI * 2
        const d = 22 + k * 9
        const sm = makeMergeOffset('hub', true)
        nodes.push({
          ox: cx + Math.cos(a) * d,
          oy: cy + Math.sin(a) * d,
          x: cx + Math.cos(a) * d,
          y: cy + Math.sin(a) * d,
          vx: 0,
          vy: 0,
          r: 3.4 - k * 0.5,
          baseAlpha: 0.78 - k * 0.08,
          tier: 'hub',
          clusterId: cl.id,
          phase: Math.random() * Math.PI * 2,
          mergeR: sm.mergeR,
          mergeA: sm.mergeA,
        })
      }
    }

    for (let i = 0; i < cl.count; i++) {
      // Gaussian 샘플링 — safe zone / 가장자리 침범 시 재시도하여
      // 경계선에 일렬로 정렬되는 현상 방지
      let ox = 0,
        oy = 0
      let attempts = 0
      while (attempts < 8) {
        const u = Math.max(Math.random(), 1e-9)
        const v = Math.max(Math.random(), 1e-9)
        const g1 = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
        const g2 = Math.sqrt(-2 * Math.log(u)) * Math.sin(2 * Math.PI * v)
        ox = cx + g1 * cl.spread
        oy = cy + g2 * cl.spread * 0.78

        const okEdge = ox > EDGE_SOFT && ox < W - EDGE_SOFT && oy > EDGE_SOFT && oy < H - EDGE_SOFT
        const okSafe = !inCopySZ(ox, oy, W, H)

        if (okEdge && okSafe) break
        attempts++
      }
      // 재시도 후에도 침범하면 — 랜덤 오프셋과 함께 부드럽게 보정
      // (Math.random 으로 직선 정렬 자체를 방지)
      if (ox < EDGE_SOFT) ox = EDGE_SOFT + 10 + Math.random() * 40
      if (ox > W - EDGE_SOFT) ox = W - EDGE_SOFT - 10 - Math.random() * 40
      if (oy < EDGE_SOFT) oy = EDGE_SOFT + 10 + Math.random() * 40
      if (oy > H - EDGE_SOFT) oy = H - EDGE_SOFT - 10 - Math.random() * 40
      if (inCopySZ(ox, oy, W, H)) {
        // 위/아래로 부드럽게 밀어냄 (랜덤 방향)
        const dy = Math.random() < 0.5 ? -1 : 1
        oy = H * 0.5 + dy * (COPY_SZ_HH + 12 + Math.random() * 20)
      }

      const distRatio = Math.hypot((ox - cx) / cl.spread, (oy - cy) / cl.spread)
      const normalThresh = cl.isMain ? 0.85 : 0.65
      const tier: NodeTier =
        distRatio < normalThresh && Math.random() > (cl.isMain ? 0.18 : 0.3)
          ? 'normal'
          : 'background'

      const m = makeMergeOffset(tier, cl.isMain)
      nodes.push({
        ox,
        oy,
        x: ox,
        y: oy,
        vx: 0,
        vy: 0,
        r:
          tier === 'normal'
            ? cl.isMain
              ? 2.3 + Math.random() * 1.1
              : 1.7 + Math.random() * 1.0
            : cl.isMain
              ? 1.1 + Math.random() * 0.6
              : 0.85 + Math.random() * 0.55,
        baseAlpha:
          tier === 'normal'
            ? cl.isMain
              ? 0.5 + Math.random() * 0.28
              : 0.42 + Math.random() * 0.28
            : cl.isMain
              ? 0.18 + Math.random() * 0.14
              : 0.12 + Math.random() * 0.16,
        tier,
        clusterId: cl.id,
        phase: Math.random() * Math.PI * 2,
        mergeR: m.mergeR,
        mergeA: m.mergeA,
      })
    }
  }
  return nodes
}

function buildPulses(nodes: NetNode[]): Pulse[] {
  const pulses: Pulse[] = []
  for (let i = 0; i < nodes.length; i++) {
    if (nodes[i].tier !== 'hub') continue
    const isCore = nodes[i].clusterId === 0
    for (let j = 0; j < nodes.length; j++) {
      if (i === j || nodes[j].clusterId !== nodes[i].clusterId) continue
      if (nodes[j].tier === 'background') continue
      const d = Math.hypot(nodes[i].ox - nodes[j].ox, nodes[i].oy - nodes[j].oy)
      const maxDist = isCore ? 200 : 120
      const prob = isCore ? 0.36 : 0.22
      if (d < maxDist && Math.random() < prob) {
        pulses.push({
          fromIdx: i,
          toIdx: j,
          t: Math.random(),
          speed: isCore ? 0.003 + Math.random() * 0.005 : 0.0025 + Math.random() * 0.004,
        })
      }
    }
  }
  return pulses
}

// ─── easing ──────────────────────────────────────────────────

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
}
function easeIn(t: number): number {
  return t * t
}
function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v))
}
function progressBand(p: number, lo: number, hi: number): number {
  return clamp01((p - lo) / (hi - lo))
}

// ─── Canvas 컴포넌트 ─────────────────────────────────────────

interface CanvasProps {
  hoveredCluster: number | null
  onClusterHover: (id: number | null) => void
  scrollProgress: number
}

function AgentCanvas({ hoveredCluster, onClusterHover, scrollProgress }: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animateRef = useRef<FrameRequestCallback | null>(null)
  const stateRef = useRef<{
    nodes: NetNode[]
    pulses: Pulse[]
    mouse: { x: number; y: number }
    lerpMouse: { x: number; y: number }
    raf: number
    W: number
    H: number
    hoveredCluster: number | null
    scrollProgress: number
  } | null>(null)

  useEffect(() => {
    if (stateRef.current) stateRef.current.hoveredCluster = hoveredCluster
  }, [hoveredCluster])

  useEffect(() => {
    if (stateRef.current) stateRef.current.scrollProgress = scrollProgress
  }, [scrollProgress])

  const INTRA = 130
  const CORE_INTRA = 200
  const BRIDGE = 280
  const SK = 0.024
  const DAMP = 0.79
  const MR = 150
  const LERP_M = 0.09
  const DRIFT = 0.55

  const queueFrame = useCallback(() => {
    const s = stateRef.current
    const animateFrame = animateRef.current
    if (!s || !animateFrame) return
    s.raf = requestAnimationFrame(animateFrame)
  }, [])

  const animate = useCallback(() => {
    const s = stateRef.current
    if (!s) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const { W, H, nodes, pulses, mouse, lerpMouse } = s
    const hc = s.hoveredCluster
    const sp = s.scrollProgress
    const t = performance.now() * 0.001

    lerpMouse.x += (mouse.x - lerpMouse.x) * LERP_M
    lerpMouse.y += (mouse.y - lerpMouse.y) * LERP_M

    // ── 2단계 진행도 ─────────────────────────────────────
    // Stage 1: 분산된 군집 → 통합 코어 cluster
    // Stage 2: 통합 코어 → 로그인 버튼 흡수
    const stage1Band = progressBand(sp, 0.18, 0.5)
    const stage1Eased = easeInOut(stage1Band)
    const stage2Band = progressBand(sp, 0.5, 0.82)
    const stage2Eased = easeInOut(stage2Band)
    const stage2Accel = easeIn(stage2Band)

    // 통합 코어 / 버튼 중심 (둘 다 화면 중앙)
    const cx = W * 0.5
    const cy = H * 0.5

    ctx.clearRect(0, 0, W * dpr, H * dpr)

    // ── 배경 ambient ─────────────────────────────────────
    const bgGrad = ctx.createRadialGradient(
      cx * dpr,
      cy * dpr,
      0,
      cx * dpr,
      cy * dpr,
      Math.min(W, H) * 0.62 * dpr,
    )
    bgGrad.addColorStop(0, `rgba(28,28,30,${0.46 * (1 - stage2Eased * 0.4)})`)
    bgGrad.addColorStop(1, 'rgba(11,11,13,0)')
    ctx.fillStyle = bgGrad
    ctx.fillRect(0, 0, W * dpr, H * dpr)

    // ── 물리 업데이트 ────────────────────────────────────
    for (const nd of nodes) {
      const isHovered = hc !== null && nd.clusterId === hc
      const driftScale = nd.tier === 'hub' ? 0.3 : 1.0

      // 자연스러운 floating motion (home position)
      const homeX = nd.ox + Math.sin(t * 0.22 + nd.phase) * DRIFT * driftScale
      const homeY = nd.oy + Math.cos(t * 0.16 + nd.phase * 1.1) * DRIFT * driftScale

      // 통합 코어 내 자리 — Stage 2 시 회전 + 반경 수축
      const orbA = nd.mergeA + stage2Accel * Math.PI * 1.6
      const orbR = nd.mergeR * (1 - stage2Eased * 0.96)
      const orbX = cx + Math.cos(orbA) * orbR
      const orbY = cy + Math.sin(orbA) * orbR * 0.85

      // Stage 1 진행: home → orbit 위치 / Stage 2: orbit는 점차 중심으로 수렴
      const tx = homeX + (orbX - homeX) * stage1Eased
      const ty = homeY + (orbY - homeY) * stage1Eased

      // Stage 2 후반 스프링 가속 — 빨려드는 느낌
      const sk = SK + stage2Accel * 0.1
      addVelocity(nd, (tx - nd.x) * sk, (ty - nd.y) * sk)

      // 마우스 인터랙션 (hero 상태에만)
      const interactStrength = clamp01(1 - stage1Band * 1.5)
      if (interactStrength > 0.02) {
        const mdx = lerpMouse.x - nd.x
        const mdy = lerpMouse.y - nd.y
        const mdist = Math.hypot(mdx, mdy)
        if (mdist < MR && mdist > 1) {
          const fac = ((MR - mdist) / MR) ** 1.6
          const pull = (isHovered ? 0.09 : 0.035) * interactStrength
          addVelocity(nd, (mdx / mdist) * fac * pull * 6, (mdy / mdist) * fac * pull * 6)
        }
      }

      // Soft repulsion — hero 상태에서만 / 점진적으로 약화
      const sgRepel = clamp01(1 - stage1Band * 1.8)
      if (sgRepel > 0.05) {
        // 카피 영역
        const sdx = nd.x - cx
        const sdy = nd.y - cy
        const penX = COPY_SZ_HW - Math.abs(sdx)
        const penY = COPY_SZ_HH - Math.abs(sdy)
        if (penX > 0 && penY > 0) {
          const push = 0.14 * sgRepel
          if (penX < penY) addVelocity(nd, Math.sign(sdx || 1) * penX * push, 0)
          else addVelocity(nd, 0, Math.sign(sdy || 1) * penY * push)
        }
        // 화면 가장자리 — soft (약한 반발)
        const er = 0.01 * sgRepel
        if (nd.x < EDGE_SOFT) addVelocity(nd, (EDGE_SOFT - nd.x) * er, 0)
        else if (nd.x > W - EDGE_SOFT) addVelocity(nd, -(nd.x - (W - EDGE_SOFT)) * er, 0)
        if (nd.y < EDGE_SOFT) addVelocity(nd, 0, (EDGE_SOFT - nd.y) * er)
        else if (nd.y > H - EDGE_SOFT) addVelocity(nd, 0, -(nd.y - (H - EDGE_SOFT)) * er)
      }

      advanceNode(nd, DAMP)
    }

    // ── pulse 업데이트 ───────────────────────────────────
    for (const p of pulses) {
      const hovered = hc !== null && nodes[p.fromIdx].clusterId === hc
      advancePulse(p, hovered ? 1.8 : 1)
    }

    // ── 연결선 ───────────────────────────────────────────
    // Stage 1 동안 노드들이 가까이 모이면서 자연스럽게 연결망이 재구성됨
    // Stage 2에서 점차 사라짐
    const lineOpMul = 1 - stage2Eased * 0.95
    if (lineOpMul > 0.02) {
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i]
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j]
          const dist = Math.hypot(a.x - b.x, a.y - b.y)
          const same = a.clusterId === b.clusterId
          const isCoreEdge = same && a.clusterId === 0
          const maxD = isCoreEdge ? CORE_INTRA : same ? INTRA : BRIDGE
          if (dist > maxD) continue
          if (!same && a.tier !== 'hub') continue
          if (!same && b.tier !== 'hub') continue

          const aHov = hc !== null && a.clusterId === hc
          const bHov = hc !== null && b.clusterId === hc
          const isActive = aHov || bHov
          const midX = (a.x + b.x) / 2
          const midY = (a.y + b.y) / 2

          // hero 상태에서만 카피 통과 차단
          if (stage1Band < 0.08) {
            if (inCopySZ(midX, midY, W, H)) continue
          }

          const mDist = Math.hypot(midX - lerpMouse.x, midY - lerpMouse.y)
          const mBoost = mDist < MR ? 1 + (1 - mDist / MR) * 1.3 : 1
          const base = same
            ? Math.pow(1 - dist / maxD, 1.6) * (a.tier === 'hub' || b.tier === 'hub' ? 0.28 : 0.11)
            : Math.pow(1 - dist / maxD, 2.2) * 0.14
          const hoverMul = isActive ? 2.0 : hc !== null ? 0.35 : 1
          const alpha = Math.min(base * mBoost * hoverMul * lineOpMul, 0.52)

          ctx.beginPath()
          ctx.moveTo(a.x * dpr, a.y * dpr)
          ctx.lineTo(b.x * dpr, b.y * dpr)
          ctx.strokeStyle = `rgba(210,210,212,${alpha.toFixed(3)})`
          ctx.lineWidth = (same ? 0.7 : 0.45) * dpr
          ctx.stroke()
        }
      }
    }

    // ── pulse ────────────────────────────────────────────
    const pulseOpMul = 1 - stage2Eased * 0.92
    if (pulseOpMul > 0.04) {
      for (const p of pulses) {
        const from = nodes[p.fromIdx]
        const to = nodes[p.toIdx]
        const px = from.x + (to.x - from.x) * p.t
        const py = from.y + (to.y - from.y) * p.t
        const fade = Math.sin(p.t * Math.PI)
        const hov = hc !== null && from.clusterId === hc
        const pa = (hov ? 0.86 : 0.48) * fade * pulseOpMul

        ctx.beginPath()
        ctx.arc(px * dpr, py * dpr, (hov ? 1.9 : 1.4) * dpr, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(218,218,220,${pa.toFixed(3)})`
        ctx.fill()
      }
    }

    // ── Stage 2: 흡수 트레일 (버튼 방향 잔상) ────────────
    if (stage2Accel > 0.1) {
      const ts = stage2Accel
      for (const nd of nodes) {
        if (nd.tier === 'background' && Math.random() < 0.5) continue
        const dx = cx - nd.x
        const dy = cy - nd.y
        const dist = Math.hypot(dx, dy)
        if (dist < 6) continue
        const nx = dx / dist,
          ny = dy / dist
        const trailLen = Math.min(dist * 0.35 * ts, 55)
        const tAlpha = (nd.tier === 'hub' ? 0.3 : 0.13) * ts
        const tg = ctx.createLinearGradient(
          nd.x * dpr,
          nd.y * dpr,
          (nd.x + nx * trailLen) * dpr,
          (nd.y + ny * trailLen) * dpr,
        )
        tg.addColorStop(0, `rgba(220,220,224,${tAlpha.toFixed(3)})`)
        tg.addColorStop(1, 'rgba(220,220,224,0)')
        ctx.beginPath()
        ctx.moveTo(nd.x * dpr, nd.y * dpr)
        ctx.lineTo((nd.x + nx * trailLen) * dpr, (nd.y + ny * trailLen) * dpr)
        ctx.strokeStyle = tg
        ctx.lineWidth = (nd.tier === 'hub' ? 1.1 : 0.65) * dpr
        ctx.stroke()
      }
    }

    // ── CORE HUB halo — Stage 1 진행 시 강해지며 코어 형성 인상 ──
    const coreHub = nodes.find((n) => n.clusterId === 0 && n.tier === 'hub')
    if (coreHub) {
      const isHov = hc === 0
      const breathe = 1 + Math.sin(t * 0.46 + coreHub.phase) * 0.08
      const formIntensity = stage1Eased * (1 - stage2Eased * 0.85)
      const ringBase = (isHov ? 0.18 : 0.08) + formIntensity * 0.16
      const haloR = (66 + Math.sin(t * 0.36) * 5 + formIntensity * 36) * breathe

      const halo = ctx.createRadialGradient(
        coreHub.x * dpr,
        coreHub.y * dpr,
        haloR * 0.36 * dpr,
        coreHub.x * dpr,
        coreHub.y * dpr,
        haloR * dpr,
      )
      halo.addColorStop(0, `rgba(210,210,214,${(ringBase * 0.65).toFixed(3)})`)
      halo.addColorStop(1, 'rgba(210,210,214,0)')
      ctx.beginPath()
      ctx.arc(coreHub.x * dpr, coreHub.y * dpr, haloR * dpr, 0, Math.PI * 2)
      ctx.fillStyle = halo
      ctx.fill()

      for (let ri = 0; ri < 2; ri++) {
        const ringR = (42 + ri * 22 + formIntensity * 18) * breathe
        const startA = t * (ri === 0 ? 0.15 : -0.1) + ri * 1.1
        const span = Math.PI * (ri === 0 ? 1.35 : 0.85)
        const rA = (ringBase + (isHov ? 0.06 : 0)) * (ri === 0 ? 1 : 0.52)
        ctx.beginPath()
        ctx.arc(coreHub.x * dpr, coreHub.y * dpr, ringR * dpr, startA, startA + span)
        ctx.strokeStyle = `rgba(210,210,214,${rA.toFixed(3)})`
        ctx.lineWidth = (ri === 0 ? 0.8 : 0.5) * dpr
        ctx.stroke()
      }
    }

    // ── Stage 2: 버튼 자리 흡수 glow ─────────────────────
    if (stage2Eased > 0.02) {
      const inner = ctx.createRadialGradient(cx * dpr, cy * dpr, 0, cx * dpr, cy * dpr, 36 * dpr)
      inner.addColorStop(0, `rgba(240,240,244,${(stage2Eased * 0.2).toFixed(3)})`)
      inner.addColorStop(1, 'rgba(240,240,244,0)')
      ctx.beginPath()
      ctx.arc(cx * dpr, cy * dpr, 36 * dpr, 0, Math.PI * 2)
      ctx.fillStyle = inner
      ctx.fill()

      const outer = ctx.createRadialGradient(
        cx * dpr,
        cy * dpr,
        26 * dpr,
        cx * dpr,
        cy * dpr,
        130 * dpr,
      )
      outer.addColorStop(0, `rgba(215,215,220,${(stage2Eased * 0.1).toFixed(3)})`)
      outer.addColorStop(1, 'rgba(215,215,220,0)')
      ctx.beginPath()
      ctx.arc(cx * dpr, cy * dpr, 130 * dpr, 0, Math.PI * 2)
      ctx.fillStyle = outer
      ctx.fill()
    }

    // ── 노드 ─────────────────────────────────────────────
    for (const nd of nodes) {
      const isCore = nd.clusterId === 0
      const isHov = hc !== null && nd.clusterId === hc
      const mDist = Math.hypot(nd.x - lerpMouse.x, nd.y - lerpMouse.y)
      const mBoost = mDist < MR ? 1 + (1 - mDist / MR) * (nd.tier === 'hub' ? 0.55 : 0.28) : 1
      const hBoost = isHov ? (isCore ? 1.65 : 1.42) : hc !== null ? (isCore ? 0.55 : 0.38) : 1
      const breathe = 1 + Math.sin(t * 0.46 + nd.phase) * (nd.tier === 'hub' ? 0.08 : 0.04)

      // Stage 2 노드 크기 수축 (빨려들기)
      const scaleShrink =
        nd.tier === 'hub'
          ? 1 - stage2Accel * 0.4
          : nd.tier === 'normal'
            ? 1 - stage2Accel * 0.65
            : 1 - stage2Accel * 0.85

      // Stage 2 페이드: background 먼저 / hub 마지막
      const tierFade =
        nd.tier === 'hub'
          ? 1 - stage2Eased * 0.55
          : nd.tier === 'normal'
            ? 1 - stage2Eased * 0.82
            : 1 - stage2Eased * 0.96

      const alpha = Math.min(nd.baseAlpha * mBoost * hBoost * breathe * tierFade, 1.0)
      const radius = Math.max(
        0.3,
        nd.r * (isHov ? (isCore ? 1.3 : 1.2) : 1) * breathe * scaleShrink,
      )

      if (alpha < 0.01) continue

      if (nd.tier === 'hub') {
        const glowMul = isCore ? (isHov ? 8.5 : 6.0) : isHov ? 6.0 : 4.2
        const glowA0 = isCore ? (isHov ? 0.32 : 0.18) : isHov ? 0.24 : 0.13
        const glow = ctx.createRadialGradient(
          nd.x * dpr,
          nd.y * dpr,
          0,
          nd.x * dpr,
          nd.y * dpr,
          radius * glowMul * dpr,
        )
        glow.addColorStop(0, `rgba(215,215,218,${(alpha * glowA0).toFixed(3)})`)
        glow.addColorStop(1, 'rgba(215,215,218,0)')
        ctx.beginPath()
        ctx.arc(nd.x * dpr, nd.y * dpr, radius * glowMul * dpr, 0, Math.PI * 2)
        ctx.fillStyle = glow
        ctx.fill()
      }

      ctx.beginPath()
      ctx.arc(nd.x * dpr, nd.y * dpr, radius * dpr, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(225,225,228,${alpha.toFixed(3)})`
      ctx.fill()
    }

    // ── 클러스터 라벨 (hero state 만) ─────────────────────
    const labelOpacity = 1 - progressBand(sp, 0.06, 0.22)
    if (labelOpacity > 0.02) {
      for (const cl of CLUSTER_DEFS) {
        const hubNode = nodes.find((n) => n.clusterId === cl.id && n.tier === 'hub')!
        const isHov = hc === cl.id
        const mDist = Math.hypot(hubNode.x - lerpMouse.x, hubNode.y - lerpMouse.y)
        const prox = Math.max(0, 1 - mDist / 190)
        const nameAlpha = (isHov ? 0.95 : 0.42 + prox * 0.36) * labelOpacity

        const vecX = cl.rx - 0.5
        const vecY = cl.ry - 0.5
        const vecLen = Math.hypot(vecX, vecY) || 1
        const ux = vecX / vecLen
        const uy = vecY / vecLen

        const margin = cl.isMain ? cl.spread * 0.65 + 30 : cl.spread * 0.55 + 20
        let lx = hubNode.x + ux * margin
        let ly = hubNode.y + uy * margin

        const fontSize = cl.isMain ? 13 : 12
        const padL = fontSize * cl.label.length * 0.5 + 14
        lx = Math.max(padL, Math.min(W - padL, lx))
        ly = Math.max(45, Math.min(H - 24, ly))

        const align: CanvasTextAlign = ux > 0.25 ? 'left' : ux < -0.25 ? 'right' : 'center'
        const baselineShift = uy > 0.2 ? 13 : uy < -0.2 ? -4 : 5

        ctx.save()
        ctx.textAlign = align
        ctx.font = `600 ${fontSize * dpr}px -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif`
        ctx.letterSpacing = `${(cl.isMain ? 2.0 : 1.6) * dpr}px`
        ctx.shadowColor = 'rgba(0,0,0,0.85)'
        ctx.shadowBlur = 8 * dpr
        ctx.fillStyle = `rgba(232,232,236,${nameAlpha.toFixed(3)})`
        ctx.fillText(cl.label, lx * dpr, (ly + baselineShift) * dpr)
        ctx.restore()

        if (nameAlpha > 0.05) {
          const tickEndX = lx - ux * 8
          const tickEndY = ly + baselineShift - uy * 8
          ctx.beginPath()
          ctx.moveTo(hubNode.x * dpr, hubNode.y * dpr)
          ctx.lineTo(tickEndX * dpr, tickEndY * dpr)
          ctx.strokeStyle = `rgba(185,185,188,${(nameAlpha * 0.28).toFixed(3)})`
          ctx.lineWidth = 0.5 * dpr
          ctx.stroke()
        }
      }
    }

    // ── 코너 브래킷 ──────────────────────────────────────
    const bkA = 0.1 * (1 - stage2Eased * 0.7)
    if (bkA > 0.01) {
      const bL = 13
      const bO = 15
      ;[
        [bO, bO, 1, 1],
        [W - bO, bO, -1, 1],
        [bO, H - bO, 1, -1],
        [W - bO, H - bO, -1, -1],
      ].forEach(([x, y, sx, sy]) => {
        ctx.beginPath()
        ctx.moveTo((x + sx * bL) * dpr, y * dpr)
        ctx.lineTo(x * dpr, y * dpr)
        ctx.lineTo(x * dpr, (y + sy * bL) * dpr)
        ctx.strokeStyle = `rgba(185,185,188,${bkA})`
        ctx.lineWidth = 0.85 * dpr
        ctx.stroke()
      })
    }

    queueFrame()
  }, [queueFrame])

  useEffect(() => {
    animateRef.current = animate
  }, [animate])

  const init = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const W = window.innerWidth
    const H = window.innerHeight
    canvas.width = W * dpr
    canvas.height = H * dpr
    canvas.style.width = `${W}px`
    canvas.style.height = `${H}px`

    const nodes = buildNetwork(W, H)
    const pulses = buildPulses(nodes)
    stateRef.current = {
      nodes,
      pulses,
      mouse: { x: W / 2, y: H / 2 },
      lerpMouse: { x: W / 2, y: H / 2 },
      raf: 0,
      W,
      H,
      hoveredCluster: null,
      scrollProgress: 0,
    }
  }, [])

  useEffect(() => {
    init()
    stateRef.current!.raf = requestAnimationFrame(animate)
    const onResize = () => {
      if (stateRef.current) cancelAnimationFrame(stateRef.current.raf)
      init()
      stateRef.current!.raf = requestAnimationFrame(animate)
    }
    window.addEventListener('resize', onResize)
    return () => {
      if (stateRef.current) cancelAnimationFrame(stateRef.current.raf)
      window.removeEventListener('resize', onResize)
    }
  }, [animate, init])

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!stateRef.current) return
      stateRef.current.mouse.x = e.clientX
      stateRef.current.mouse.y = e.clientY

      // hero 상태에서만 hover 감지
      if (stateRef.current.scrollProgress > 0.14) {
        onClusterHover(null)
        return
      }

      const { nodes, W, H } = stateRef.current
      let closest: number | null = null
      let minDist = 9999
      for (const cl of CLUSTER_DEFS) {
        const hub = nodes.find((n) => n.clusterId === cl.id && n.tier === 'hub')
        if (!hub) continue
        const d = Math.hypot(hub.x - e.clientX, hub.y - e.clientY)
        const r = Math.min(W, H) * cl.hoverDetectR
        if (d < r && d < minDist) {
          minDist = d
          closest = cl.id
        }
      }
      onClusterHover(closest)
    },
    [onClusterHover],
  )

  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove)
    return () => window.removeEventListener('mousemove', onMouseMove)
  }, [onMouseMove])

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'fixed', inset: 0, display: 'block', pointerEvents: 'none' }}
    />
  )
}

// ─── 카카오 아이콘 ───────────────────────────────────────────

function KakaoIcon() {
  return (
    <svg width="18" height="17" viewBox="0 0 24 22" fill="currentColor" aria-hidden>
      <path d="M12 2C5.93 2 1 5.97 1 10.86c0 3.13 2 5.88 5.05 7.55l-1.28 4.7c-.11.42.37.76.74.51l5.55-3.69c.31.04.62.06.94.06 6.07 0 11-3.97 11-8.86C23 5.97 18.07 2 12 2z" />
    </svg>
  )
}

// ─── 페이지 ──────────────────────────────────────────────────

export function LoginPage() {
  const navigate = useNavigate()
  const { setTokens, setUserInfo } = useAuthStore()
  const [hoveredCluster, setHoveredCluster] = useState<number | null>(null)
  const [scrollProgress, setScrollProgress] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  const handleKakaoLogin = () => {
    window.location.href = KAKAO_AUTH_URL
  }

  const handleDevLogin = async () => {
    try {
      const res = await devLogin()
      setTokens(res.data.accessToken, res.data.refreshToken)
      try {
        const userRes = await getMyInfo()
        setUserInfo(userRes.data)
      } catch {
        /* ignore */
      }
      navigate('/', { replace: true })
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const onScroll = () => {
      const maxScroll = el.scrollHeight - el.clientHeight
      setScrollProgress(maxScroll > 0 ? el.scrollTop / maxScroll : 0)
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  const hovered =
    hoveredCluster !== null ? (CLUSTER_DEFS.find((c) => c.id === hoveredCluster) ?? null) : null

  // Hero copy — 빠르게 fade out (Stage 1 시작 전 사라짐)
  const copyOpacity = clamp01(1 - progressBand(scrollProgress, 0.06, 0.22))
  const copyTranslateY = progressBand(scrollProgress, 0.06, 0.22) * -28

  // 로그인 버튼 — Stage 2 시점부터 등장 (fade + 가벼운 translateY)
  const loginOpacity = clamp01(progressBand(scrollProgress, 0.55, 0.78))
  const loginTranslateY = (1 - loginOpacity) * 18

  // Stage 2 끝 무렵부터 살짝 추가 강조 ("응축된 진입점" 느낌)
  const loginEmphasis = clamp01(progressBand(scrollProgress, 0.78, 0.92))

  const hintOpacity = clamp01(1 - progressBand(scrollProgress, 0.02, 0.12))

  return (
    <div
      ref={scrollRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        overflowY: 'scroll',
        backgroundColor: '#0B0B0D',
        scrollbarWidth: 'none',
      }}
    >
      <style>{`
        div::-webkit-scrollbar { display: none }
        @keyframes scrollHintBounce {
          0%, 100% { transform: translateY(0); }
          50%       { transform: translateY(5px); }
        }
        @keyframes scrollDot {
          0%, 100% { opacity: 0.42; transform: translateY(0); }
          50%       { opacity: 0.78; transform: translateY(2px); }
        }
      `}</style>

      {/* 스크롤 거리 — 400vh */}
      <div style={{ height: '400vh', position: 'relative' }}>
        <AgentCanvas
          hoveredCluster={hoveredCluster}
          onClusterHover={setHoveredCluster}
          scrollProgress={scrollProgress}
        />

        {/* vignette */}
        <div
          style={{
            position: 'fixed',
            inset: 0,
            pointerEvents: 'none',
            zIndex: 1,
            background:
              'radial-gradient(ellipse 55% 52% at 50% 50%, rgba(11,11,13,0.50) 0%, transparent 100%)',
          }}
        />

        {/* hover tooltip — hero state 만 */}
        <div
          style={{
            position: 'fixed',
            top: 24,
            right: 26,
            zIndex: 20,
            pointerEvents: 'none',
            opacity: hovered && scrollProgress < 0.13 ? 1 : 0,
            transform: `translateY(${hovered ? 0 : 6}px)`,
            transition: 'opacity 0.20s ease, transform 0.20s ease',
          }}
        >
          {hovered && (
            <div
              style={{
                background: 'rgba(14,14,16,0.96)',
                border: `1px solid rgba(210,210,214,${hovered.isMain ? 0.22 : 0.14})`,
                borderRadius: 12,
                padding: hovered.isMain ? '14px 18px' : '12px 16px',
                backdropFilter: 'blur(20px)',
                minWidth: hovered.isMain ? 252 : 210,
                maxWidth: 280,
                boxShadow: '0 4px 28px rgba(0,0,0,0.55)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9 }}>
                <div
                  style={{
                    width: hovered.isMain ? 6 : 5,
                    height: hovered.isMain ? 6 : 5,
                    borderRadius: '50%',
                    background: 'rgba(225,225,228,0.82)',
                    flexShrink: 0,
                  }}
                />
                <p
                  style={{
                    color: 'rgba(238,238,242,1)',
                    fontSize: hovered.isMain ? 13 : 12,
                    fontFamily:
                      '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
                    letterSpacing: '0.10em',
                    fontWeight: 700,
                    margin: 0,
                    textTransform: 'uppercase',
                  }}
                >
                  {hovered.title}
                </p>
              </div>
              <p
                style={{
                  color: 'rgba(178,178,184,0.90)',
                  fontSize: 13,
                  lineHeight: 1.68,
                  marginBottom: hovered.keywords ? 10 : 0,
                  wordBreak: 'keep-all',
                  fontFamily:
                    '-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif',
                }}
              >
                {hovered.desc}
              </p>
              {hovered.keywords && (
                <p
                  style={{
                    color: 'rgba(148,148,154,0.58)',
                    fontSize: 10.5,
                    fontFamily:
                      '-apple-system, BlinkMacSystemFont, "SF Mono", "Fira Code", monospace',
                    letterSpacing: '0.04em',
                    borderTop: '1px solid rgba(210,210,214,0.10)',
                    paddingTop: 9,
                    margin: 0,
                    lineHeight: 1.5,
                  }}
                >
                  {hovered.keywords}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Hero 카피 — 한글 */}
        <div
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: `translate(-50%, calc(-50% + ${copyTranslateY}px))`,
            opacity: copyOpacity,
            zIndex: 10,
            pointerEvents: 'none',
            textAlign: 'center',
            transition: 'none',
            width: 'min(86vw, 380px)',
          }}
        >
          <h1
            style={{
              color: '#F2F2F4',
              fontSize: 'clamp(26px, 3.8vw, 40px)',
              fontWeight: 600,
              letterSpacing: '-0.022em',
              margin: 0,
              lineHeight: 1.14,
              fontFamily:
                '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
            }}
          >
            Your agent is ready
          </h1>
          <p
            style={{
              color: 'rgba(165,165,170,0.86)',
              fontSize: 14,
              lineHeight: 1.72,
              marginTop: 14,
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            }}
          >
            Connect to your memory, planning, health,
            <br />
            and sync agents in one intelligent workspace.
          </p>
        </div>

        {/* Login reveal — Stage 2 시점부터 등장 */}
        <div
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: `translate(-50%, calc(-50% + ${loginTranslateY}px))`,
            opacity: loginOpacity,
            zIndex: 15,
            width: 308,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 14,
            pointerEvents: loginOpacity > 0.5 ? 'auto' : 'none',
            transition: 'none',
          }}
        >
          <p
            style={{
              color: `rgba(148,148,154,${loginOpacity * 0.62})`,
              fontSize: 10,
              fontFamily: 'monospace',
              letterSpacing: '0.18em',
              margin: 0,
              textTransform: 'uppercase',
            }}
          >
            Agent System Online
          </p>

          <button
            onClick={handleKakaoLogin}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              borderRadius: 12,
              padding: '14px 24px',
              fontSize: 15,
              fontWeight: 700,
              fontFamily:
                '-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif',
              background: '#FEE500',
              color: '#191919',
              border: 'none',
              boxShadow: `0 6px 24px rgba(0,0,0,0.50), 0 0 ${20 + loginEmphasis * 18}px rgba(254,229,0,${0.18 + loginEmphasis * 0.18})`,
              cursor: 'pointer',
              transition: 'background 0.16s ease, transform 0.16s ease, box-shadow 0.20s ease',
              letterSpacing: '-0.01em',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#FFE91A'
              e.currentTarget.style.transform = 'translateY(-1px)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#FEE500'
              e.currentTarget.style.transform = 'translateY(0)'
            }}
          >
            <KakaoIcon />
            카카오 계정으로 로그인
          </button>

          {import.meta.env.DEV && (
            <button
              onClick={handleDevLogin}
              style={{
                width: '100%',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(210,210,214,0.16)',
                color: 'rgba(190,190,194,0.66)',
                borderRadius: 10,
                padding: '10px 24px',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif',
                transition: 'border-color 0.15s, color 0.15s, background 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(210,210,214,0.34)'
                e.currentTarget.style.color = 'rgba(220,220,224,0.90)'
                e.currentTarget.style.background = 'rgba(255,255,255,0.06)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(210,210,214,0.16)'
                e.currentTarget.style.color = 'rgba(190,190,194,0.66)'
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              }}
            >
              개발용 테스트 로그인
            </button>
          )}
        </div>

        {/* Scroll hint */}
        <div
          style={{
            position: 'fixed',
            bottom: 34,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 10,
            opacity: hintOpacity,
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 7,
            transition: 'none',
          }}
        >
          <p
            style={{
              color: 'rgba(168,168,172,0.36)',
              fontSize: 9,
              fontFamily: 'monospace',
              letterSpacing: '0.18em',
              margin: 0,
            }}
          >
            SCROLL
          </p>
          <svg
            width="16"
            height="26"
            viewBox="0 0 16 26"
            fill="none"
            style={{ animation: 'scrollHintBounce 1.9s ease-in-out infinite' }}
          >
            <rect
              x="5.5"
              y="0.5"
              width="5"
              height="9"
              rx="2.5"
              stroke="rgba(168,168,172,0.28)"
              strokeWidth="1"
            />
            <rect
              x="7"
              y="3"
              width="2"
              height="3"
              rx="1"
              fill="rgba(168,168,172,0.42)"
              style={{ animation: 'scrollDot 1.9s ease-in-out infinite' }}
            />
            <path
              d="M4 18l4 5 4-5"
              stroke="rgba(168,168,172,0.24)"
              strokeWidth="1"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* footer */}
        <p
          style={{
            position: 'fixed',
            bottom: 18,
            right: 26,
            color: 'rgba(168,168,172,0.14)',
            fontSize: 11,
            zIndex: 10,
            margin: 0,
            opacity: clamp01(1 - scrollProgress * 3),
            pointerEvents: 'none',
          }}
        >
          © 2025 HeyGent
        </p>
      </div>
    </div>
  )
}
