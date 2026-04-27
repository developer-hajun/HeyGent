import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/useAuthStore'

// _retry 플래그 타입 확장 (무한 재시도 방지용)
interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

// 토큰 갱신 중 들어온 요청들을 대기시키는 큐
type QueueItem = {
  resolve: (token: string) => void
  reject: (err: unknown) => void
}

let isRefreshing = false
let failedQueue: QueueItem[] = []

const processQueue = (error: unknown, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token!)
  })
  failedQueue = []
}

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
})

// 요청 인터셉터: accessToken 헤더 자동 삽입
axiosInstance.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 응답 인터셉터: 401 시 토큰 재발급 후 원래 요청 재시도
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryConfig

    // 401이 아니거나, 이미 재시도한 요청이면 그냥 reject
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // refresh 엔드포인트 자체가 401이면 재시도 없이 로그아웃
    if (originalRequest.url === '/api/v1/auth/refresh') {
      useAuthStore.getState().clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 이미 갱신 중이면 큐에 넣고 대기
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return axiosInstance(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    const storedRefreshToken = useAuthStore.getState().refreshToken

    if (!storedRefreshToken) {
      useAuthStore.getState().clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    try {
      // 순환 참조를 피하기 위해 axiosInstance 직접 호출
      const { data } = await axiosInstance.post(
        '/api/v1/auth/refresh',
        {},
        { headers: { 'Refresh-Token': storedRefreshToken } },
      )
      const { accessToken, refreshToken } = data.data as {
        accessToken: string
        refreshToken: string
      }

      useAuthStore.getState().setTokens(accessToken, refreshToken)
      axiosInstance.defaults.headers.common.Authorization = `Bearer ${accessToken}`

      processQueue(null, accessToken)
      originalRequest.headers.Authorization = `Bearer ${accessToken}`
      return axiosInstance(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      useAuthStore.getState().clearTokens()
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default axiosInstance
