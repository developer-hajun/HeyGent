importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js')

const params = new URL(location.href).searchParams

firebase.initializeApp({
  apiKey: params.get('apiKey'),
  authDomain: params.get('authDomain'),
  projectId: params.get('projectId'),
  storageBucket: params.get('storageBucket'),
  messagingSenderId: params.get('messagingSenderId'),
  appId: params.get('appId'),
})

const messaging = firebase.messaging()

messaging.onBackgroundMessage((payload) => {
  const title = payload.notification?.title ?? '새 알림'
  const body = payload.notification?.body ?? ''
  const icon = '/favicon_dark.png'

  self.registration.showNotification(title, {
    body,
    icon,
    data: payload.data ?? {},
  })

  // 백그라운드 상태의 웹 클라이언트에도 알려서 메시지를 갱신하게 한다
  self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
    clients.forEach((client) => {
      client.postMessage({ type: 'FCM_BACKGROUND', data: payload.data ?? {} })
    })
  })
})
