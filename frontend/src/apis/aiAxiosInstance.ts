import axios from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/useAuthStore'

interface RetryConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

type QueueItem = {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}

let isRefreshing = false
let failedQueue: QueueItem[] = []

const aiApiBaseUrl =
  import.meta.env.VITE_AI_API_BASE_URL ??
  getAiApiBaseUrlFromWs(import.meta.env.VITE_AI_WS_BASE_URL) ??
  'http://localhost:8000/ai/api/v1'

const processQueue = (error: unknown, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token ?? '')
  })
  failedQueue = []
}

const aiAxiosInstance = axios.create({
  baseURL: aiApiBaseUrl,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

aiAxiosInstance.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

aiAxiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryConfig | undefined
    if (error.response?.status !== 401 || originalRequest === undefined || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return aiAxiosInstance(originalRequest)
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
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/refresh`,
        {},
        {
          headers: {
            'Content-Type': 'application/json',
            'Refresh-Token': storedRefreshToken,
          },
        },
      )
      const { accessToken, refreshToken } = data.data as {
        accessToken: string
        refreshToken: string
      }
      useAuthStore.getState().setTokens(accessToken, refreshToken)
      aiAxiosInstance.defaults.headers.common.Authorization = `Bearer ${accessToken}`
      processQueue(null, accessToken)
      originalRequest.headers.Authorization = `Bearer ${accessToken}`
      return aiAxiosInstance(originalRequest)
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

export default aiAxiosInstance

function getAiApiBaseUrlFromWs(wsUrl: unknown): string | undefined {
  if (typeof wsUrl !== 'string' || wsUrl.trim() === '') {
    return undefined
  }
  return wsUrl
    .replace(/^ws:/, 'http:')
    .replace(/^wss:/, 'https:')
    .replace(/\/realtime\/user\/ws\/?$/, '')
}
