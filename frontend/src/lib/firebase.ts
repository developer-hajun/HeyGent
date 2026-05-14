import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'
import type { Messaging } from 'firebase/messaging'

const apiKey = import.meta.env.VITE_FIREBASE_API_KEY as string | undefined

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET as string,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string,
}

export const isFirebaseConfigured = (): boolean =>
  typeof apiKey === 'string' && apiKey.trim() !== ''

let messaging: Messaging | null = null

export const getFirebaseMessaging = (): Messaging | null => {
  if (!isFirebaseConfigured()) return null
  if (messaging) return messaging
  try {
    const app = initializeApp(firebaseConfig)
    messaging = getMessaging(app)
    return messaging
  } catch {
    return null
  }
}

export const registerFcmServiceWorker = async (): Promise<ServiceWorkerRegistration | null> => {
  if (!('serviceWorker' in navigator)) return null

  const swUrl = new URL('/firebase-messaging-sw.js', window.location.origin)
  swUrl.searchParams.set('apiKey', firebaseConfig.apiKey)
  swUrl.searchParams.set('authDomain', firebaseConfig.authDomain)
  swUrl.searchParams.set('projectId', firebaseConfig.projectId)
  swUrl.searchParams.set('storageBucket', firebaseConfig.storageBucket)
  swUrl.searchParams.set('messagingSenderId', firebaseConfig.messagingSenderId)
  swUrl.searchParams.set('appId', firebaseConfig.appId)

  try {
    return await navigator.serviceWorker.register(swUrl.toString())
  } catch {
    return null
  }
}

export { getToken, onMessage }
