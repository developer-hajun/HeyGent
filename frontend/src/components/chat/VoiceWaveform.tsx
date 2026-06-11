import { useEffect, useRef, useState } from 'react'

const BAR_COUNT = 28
const SMOOTHING = 0.35 // 0~1 — 낮을수록 반응이 즉각적
const NOISE_FLOOR = 0.02 // 이 값 이하는 0으로 간주 (배경 잡음 제거)

type VoiceWaveformProps = {
  active: boolean
  onError?: (message: string) => void
}

/**
 * 실시간 마이크 음량을 시각화하는 웨이브 바.
 * - active=true 일 때 getUserMedia 로 마이크를 열고 AnalyserNode 로 주파수 분석
 * - 주파수 스펙트럼을 BAR_COUNT 개로 분할해 각 바의 높이를 결정
 * - 음성이 없을 때는 idle 애니메이션 (작은 진동)
 */
export function VoiceWaveform({ active, onError }: VoiceWaveformProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const barRefs = useRef<HTMLDivElement[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const rafRef = useRef<number | null>(null)
  const smoothedRef = useRef<Float32Array>(new Float32Array(BAR_COUNT))
  const [ready, setReady] = useState(false)

  // 마이크 시작 / 정지
  useEffect(() => {
    if (!active) return

    let cancelled = false

    const start = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error('이 브라우저는 마이크 입력을 지원하지 않습니다.')
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        })
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream

        const AudioCtor =
          window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        if (!AudioCtor) throw new Error('AudioContext is not supported')

        const audioCtx = new AudioCtor()
        // Chrome autoplay 정책으로 suspended 상태인 경우가 있어 명시적으로 resume
        if (audioCtx.state === 'suspended') {
          await audioCtx.resume().catch(() => undefined)
        }

        const source = audioCtx.createMediaStreamSource(stream)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 512
        analyser.smoothingTimeConstant = 0.15 // 낮춰서 반응 속도 향상
        analyser.minDecibels = -85
        analyser.maxDecibels = -10
        source.connect(analyser)

        audioCtxRef.current = audioCtx
        analyserRef.current = analyser
        setReady(true)
      } catch (err) {
        const msg = err instanceof Error ? err.message : '마이크 권한이 필요합니다.'
        console.warn('[VoiceWaveform] mic init failed:', err)
        onError?.(msg)
      }
    }

    void start()

    return () => {
      cancelled = true
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
      analyserRef.current?.disconnect()
      analyserRef.current = null
      audioCtxRef.current?.close().catch(() => undefined)
      audioCtxRef.current = null
      streamRef.current?.getTracks().forEach((t) => t.stop())
      streamRef.current = null
      setReady(false)
      smoothedRef.current = new Float32Array(BAR_COUNT)
    }
  }, [active, onError])

  // 렌더 루프 — analyser 가 준비되면 매 프레임 바 높이 갱신
  useEffect(() => {
    if (!active || !ready) return
    const analyser = analyserRef.current
    if (!analyser) return

    const buffer = new Uint8Array(analyser.frequencyBinCount)
    const smoothed = smoothedRef.current

    const tick = () => {
      analyser.getByteFrequencyData(buffer)

      // 주파수 빈을 BAR_COUNT 개의 그룹으로 분할.
      // 음성 대역(약 100Hz~3.5kHz)이 시각적으로 잘 보이도록 로그 스케일 적용.
      // analyser.frequencyBinCount = fftSize/2 = 256 빈 (각 빈 ≈ sampleRate/fftSize Hz)
      const binCount = buffer.length
      // 음성 핵심 대역만 사용 (대략 80Hz~4kHz, 빈 약 2~92)
      const binStart = 2
      const binEnd = Math.min(binCount, Math.floor(binCount * 0.4))
      const usableBins = binEnd - binStart

      for (let i = 0; i < BAR_COUNT; i++) {
        const t0 = Math.pow(i / BAR_COUNT, 1.4)
        const t1 = Math.pow((i + 1) / BAR_COUNT, 1.4)
        const s = binStart + Math.floor(t0 * usableBins)
        const e = Math.max(s + 1, binStart + Math.floor(t1 * usableBins))
        let sum = 0
        for (let j = s; j < e; j++) sum += buffer[j]
        let avg = sum / (e - s) / 255 // 0~1

        // 노이즈 플로어 제거
        avg = avg < NOISE_FLOOR ? 0 : (avg - NOISE_FLOOR) / (1 - NOISE_FLOOR)
        // 작은 음량도 시각적으로 잘 보이도록 gamma 0.5 적용 (값 부풀리기)
        const target = Math.pow(avg, 0.5)

        // 빠른 attack, 느린 decay (목소리 변화에 즉각 반응)
        const prev = smoothed[i]
        smoothed[i] =
          target > prev
            ? prev * 0.15 + target * 0.85 // 빠른 상승
            : prev * SMOOTHING + target * (1 - SMOOTHING) // 부드러운 하강
      }

      // DOM 직접 갱신
      for (let i = 0; i < BAR_COUNT; i++) {
        const bar = barRefs.current[i]
        if (!bar) continue
        const v = smoothed[i]
        const heightPct = 10 + v * 90 // 10% ~ 100%
        const opacity = 0.45 + v * 0.55
        bar.style.height = `${heightPct}%`
        bar.style.opacity = `${opacity}`
      }

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [active, ready])

  return (
    <div
      ref={containerRef}
      className="flex h-9 flex-1 items-center justify-center gap-0.75"
      aria-label="음성 입력 음량 시각화"
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => {
            if (el) barRefs.current[i] = el
          }}
          className="w-0.75 rounded-full bg-red-500"
          style={{
            height: ready ? '10%' : `${10 + Math.sin(i * 0.7) * 4}%`,
            opacity: ready ? 0.5 : 0.35,
            animation: ready
              ? undefined
              : `voiceIdle ${1.2 + (i % 5) * 0.12}s ease-in-out infinite`,
            animationDelay: `${i * 0.04}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes voiceIdle {
          0%, 100% { height: 14%; opacity: 0.32; }
          50%       { height: 26%; opacity: 0.48; }
        }
      `}</style>
    </div>
  )
}
