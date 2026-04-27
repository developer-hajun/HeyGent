import axiosInstance from './axiosInstance'

// ── Types ──────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: number
  kakaoId: number
  nickname: string | null
  profileImage: string | null
  createdAt: string
  updatedAt: string
}

export interface GetMyInfoResponse {
  status: number
  message: string
  data: UserInfo
}

export interface UpdateMyInfoRequest {
  nickname?: string | null
  profileImage?: string | null
}

export interface UpdateMyInfoResponse {
  status: number
  message: string
  data: UserInfo
}

// ── API ────────────────────────────────────────────────────────────────────

/**
 * GET /api/v1/users/me
 * 로그인된 사용자 정보를 조회합니다.
 * Authorization 헤더는 axiosInstance 인터셉터가 자동으로 삽입합니다.
 */
export const getMyInfo = async (): Promise<GetMyInfoResponse> => {
  const { data } = await axiosInstance.get<GetMyInfoResponse>('/api/v1/users/me')
  return data
}

/**
 * PATCH /api/v1/users/me
 * 닉네임, 프로필 이미지를 부분 수정합니다. 전달하지 않은 필드는 변경되지 않습니다.
 * Authorization 헤더는 axiosInstance 인터셉터가 자동으로 삽입합니다.
 */
export const updateMyInfo = async (body: UpdateMyInfoRequest): Promise<UpdateMyInfoResponse> => {
  const { data } = await axiosInstance.patch<UpdateMyInfoResponse>('/api/v1/users/me', body)
  return data
}
