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

type FcmProviderProps = { children: ReactNode }

export function FcmProvider({ children }: FcmProviderProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY as string | undefined

  useEffect(() => {
    if (!isAuthenticated || !isFirebaseConfigured() || !vapidKey) return
    if (!('Notification' in window)) return

    let unsubscribeForeground: (() => void) | null = null

    const init = async () => {
      const permission = await Notification.requestPermission()
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
        if (token) {
          await registerFcmToken(token)
        }
      } catch {
        // 토큰 등록 실패는 조용히 무시 (알림 기능 미지원 환경)
        return
      }

      unsubscribeForeground = onMessage(messaging, (payload) => {
        const title = payload.notification?.title ?? '새 알림'
        const body = payload.notification?.body
        toast(title, { description: body })
      })
    }

    void init()

    return () => {
      unsubscribeForeground?.()
    }
  }, [isAuthenticated, vapidKey])

  return children
}
