import axiosInstance from './axiosInstance'

// ── Types ──────────────────────────────────────────────────────────────────

export interface KakaoLoginRequest {
  code: string
}

export interface KakaoLoginResponse {
  status: number
  message: string
  data: {
    accessToken: string
    refreshToken: string
  }
}

export interface LogoutResponse {
  status: number
  message: string
}

export interface RefreshTokenResponse {
  status: number
  message: string
  data: {
    accessToken: string
    refreshToken: string
  }
}

// ── API ────────────────────────────────────────────────────────────────────

/**
 * POST /api/v1/auth/kakao
 * 카카오 인가 코드로 로그인하고 JWT 토큰을 발급받습니다.
 */
export const kakaoLogin = async (code: string): Promise<KakaoLoginResponse> => {
  const { data } = await axiosInstance.post<KakaoLoginResponse>('/api/v1/auth/kakao', {
    code,
  } satisfies KakaoLoginRequest)
  return data
}

/**
 * POST /api/v1/auth/logout
 * Refresh Token을 기반으로 로그아웃 처리합니다.
 * Authorization 헤더는 axiosInstance 인터셉터가 자동으로 삽입합니다.
 */
export const logout = async (refreshToken: string): Promise<LogoutResponse> => {
  const { data } = await axiosInstance.post<LogoutResponse>(
    '/api/v1/auth/logout',
    {},
    { headers: { 'Refresh-Token': refreshToken } },
  )
  return data
}

/**
 * POST /api/v1/auth/refresh
 * Refresh Token으로 새 Access Token을 재발급받습니다.
 * 일반적으로 axiosInstance 인터셉터가 자동으로 처리하며,
 * 이 함수는 수동 갱신이 필요한 경우에 사용합니다.
 */
export const refreshAccessToken = async (refreshToken: string): Promise<RefreshTokenResponse> => {
  const { data } = await axiosInstance.post<RefreshTokenResponse>(
    '/api/v1/auth/refresh',
    {},
    { headers: { 'Refresh-Token': refreshToken } },
  )
  return data
}

/**
 * POST /api/v1/auth/dev-login
 * 개발 환경 전용 테스트 로그인입니다. 요청 바디 없이 호출합니다.
 */
export const devLogin = async (): Promise<KakaoLoginResponse> => {
  const { data } = await axiosInstance.post<KakaoLoginResponse>('/api/v1/auth/dev-login')
  return data
}
