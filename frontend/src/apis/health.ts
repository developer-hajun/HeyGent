import axiosInstance from './axiosInstance'

export interface HealthSummaryData {
  measuredAt: string
  // 활동
  stepCount: number | null
  activeMinutes: number | null
  totalCalories: number | null
  activeCalories: number | null
  // 체성분
  heightCm: number | null
  weightKg: number | null
  bodyFatPct: number | null
  muscleMassKg: number | null
  // 활력
  heartRateBpm: number | null
  systolicBp: number | null
  diastolicBp: number | null
  // 수면
  durationMinutes: number | null
  sleepScore: number | null
}

interface HealthSummaryResponse {
  status: number
  message: string
  data?: HealthSummaryData
}

export async function getLatestHealthData(): Promise<HealthSummaryData | null> {
  const { data } = await axiosInstance.get<HealthSummaryResponse>('/api/v1/health/me/latest')
  return data.data ?? null
}
