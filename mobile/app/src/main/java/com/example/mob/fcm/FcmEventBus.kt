package com.example.mob.fcm

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * FCM 수신 이벤트를 ChatViewModel로 전달하는 싱글톤 버스.
 * FcmMessagingService(Service)와 ChatViewModel(ViewModel) 사이의 브릿지.
 */
object FcmEventBus {
    private val _sessionRefreshEvent = MutableSharedFlow<String?>(extraBufferCapacity = 1)

    /** 수신된 sessionId (null이면 현재 열려있는 세션 갱신) */
    val sessionRefreshEvent: SharedFlow<String?> = _sessionRefreshEvent.asSharedFlow()

    fun emitRefresh(sessionId: String?) {
        _sessionRefreshEvent.tryEmit(sessionId)
    }
}
