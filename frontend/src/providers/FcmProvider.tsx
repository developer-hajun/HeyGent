import { useEffect, type ReactNode } from 'react'
import { toast } from 'sonner'
import { registerFcmToken } from '@/apis/fcm'
import {
  getFirebaseMessaging,
  getToken,
  isFirebaseConfigured,
  onMessage,
  registerFcmServiceWorker,
} from '@/lib/firebase'
import { useAuthStore } from '@/store/useAuthStore'
import { useChatStore } from '@/store/useChatStore'

type FcmProviderProps = { children: ReactNode }

export function FcmProvider({ children }: FcmProviderProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY as string | undefined

  useEffect(() => {
    if (!isAuthenticated) return
    if (!isFirebaseConfigured()) {
      console.warn('[FCM] Firebase 환경변수가 설정되지 않았습니다.')
      return
    }
    if (!vapidKey) {
      console.warn('[FCM] VITE_FIREBASE_VAPID_KEY가 설정되지 않았습니다.')
      return
    }
    if (!('Notification' in window)) {
      console.warn('[FCM] 이 브라우저는 알림을 지원하지 않습니다.')
      return
    }

    let unsubscribeForeground: (() => void) | null = null

    const handleRefresh = (sessionId: string | undefined) => {
      void useChatStore.getState().fetchSessions()
      if (sessionId) {
        void useChatStore.getState().fetchMessages(sessionId)
      }
    }

    const handleSwMessage = (event: MessageEvent) => {
      if (event.data?.type === 'FCM_BACKGROUND') {
        console.info('[FCM] 백그라운드 메시지 수신 (SW):', event.data)
        handleRefresh(event.data.data?.sessionId)
      }
    }

    navigator.serviceWorker.addEventListener('message', handleSwMessage)

    const init = async () => {
      console.info('[FCM] 알림 권한 요청 중...')
      const permission = await Notification.requestPermission()
      console.info('[FCM] 알림 권한:', permission)
      if (permission !== 'granted') return

      const registration = await registerFcmServiceWorker()
      if (!registration) return

      const messaging = getFirebaseMessaging()
      if (!messaging) return

      try {
        const token = await getToken(messaging, {
          vapidKey,
          serviceWorkerRegistration: registration,
        })
        console.info('[FCM] 토큰 발급:', token ? '성공' : '실패')
        if (token) {
          await registerFcmToken(token)
          console.info('[FCM] 백엔드 토큰 등록 완료')
        }
      } catch (e) {
        console.warn('[FCM] 토큰 등록 실패:', e)
        return
      }

      unsubscribeForeground = onMessage(messaging, (payload) => {
        console.info('[FCM] 포그라운드 메시지 수신:', payload)
        const title = payload.notification?.title ?? '새 알림'
        const body = payload.notification?.body
        handleRefresh(payload.data?.sessionId)
        toast(title, { description: body })
      })
    }

    void init()

    return () => {
      unsubscribeForeground?.()
      navigator.serviceWorker.removeEventListener('message', handleSwMessage)
    }
  }, [isAuthenticated, vapidKey])

  return children
}
