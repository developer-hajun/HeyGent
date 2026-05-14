package com.example.mob.data.remote

import android.util.Log
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** WebSocket으로 수신한 태스크 이벤트 */
data class WsTaskEvent(
    val taskRunId: String,
    val type: String,
    val raw: JSONObject,
)

/**
 * AI 백엔드 실시간 WebSocket 클라이언트.
 *
 * 경로: wss://.../ai/api/v1/realtime/user/ws
 *
 * 프로토콜:
 *  1) connect
 *  2) send {"type":"auth.start","accessToken":"..."} → receive {"type":"auth.ok"}
 *  3) send {"type":"subscribe.task","taskRunId":"..."} → receive {"type":"subscribed"}
 *  4) receive task events (type, taskRunId, payload, ...)
 */
class ChatWebSocketClient {

    companion object {
        private const val TAG = "ChatWS"
        // wss:// = WebSocket over TLS  (https → wss 변환)
        private const val WS_URL = "wss://k14e105.p.ssafy.io/ai/api/v1/realtime/user/ws"
    }

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)          // WS는 타임아웃 없이 열어 둠
        .pingInterval(30, TimeUnit.SECONDS)             // OkHttp 자동 ping
        .build()

    private var ws: WebSocket? = null
    private val authenticated = AtomicBoolean(false)
    private val pendingSubscriptions = mutableListOf<String>()

    // 외부에서 collect 가능한 태스크 이벤트 스트림
    private val _events = MutableSharedFlow<WsTaskEvent>(extraBufferCapacity = 32)
    val events: SharedFlow<WsTaskEvent> = _events.asSharedFlow()

    // 연결 상태 (true = 인증까지 완료된 상태)
    private val _connected = MutableSharedFlow<Boolean>(replay = 1, extraBufferCapacity = 1)
    val connected: SharedFlow<Boolean> = _connected.asSharedFlow()

    /** 연결 + 인증. 이미 연결 중이면 무시. */
    fun connect(accessToken: String) {
        if (ws != null) return
        Log.d(TAG, "WebSocket 연결 시도")
        val req = Request.Builder().url(WS_URL).build()
        ws = client.newWebSocket(req, object : WebSocketListener() {
            override fun onOpen(socket: WebSocket, response: Response) {
                Log.d(TAG, "연결 완료, 인증 메시지 전송")
                socket.send(
                    JSONObject().apply {
                        put("type", "auth.start")
                        put("accessToken", accessToken)
                    }.toString()
                )
            }

            override fun onMessage(socket: WebSocket, text: String) {
                try { handleMessage(text) } catch (e: Exception) {
                    Log.e(TAG, "메시지 처리 오류: ${e.message}")
                }
            }

            override fun onClosed(socket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "연결 종료: code=$code reason=$reason")
                reset()
            }

            override fun onFailure(socket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "연결 실패: ${t.message}")
                reset()
            }
        })
    }

    private fun reset() {
        authenticated.set(false)
        ws = null
        _connected.tryEmit(false)
    }

    private fun handleMessage(text: String) {
        val msg = JSONObject(text)
        when (val type = msg.optString("type")) {
            "auth.ok" -> {
                Log.d(TAG, "인증 성공 — userId=${msg.optString("userId")}")
                authenticated.set(true)
                _connected.tryEmit(true)
                // 연결 전에 쌓인 구독 요청 처리
                pendingSubscriptions.toList().also { pendingSubscriptions.clear() }
                    .forEach { doSubscribe(it) }
            }
            "auth.failed", "auth.timeout", "auth.required" -> {
                Log.e(TAG, "인증 실패: $type")
                disconnect()
            }
            "subscribed" -> {
                Log.d(TAG, "구독 성공: taskRunId=${msg.optString("taskRunId")}")
            }
            "pong" -> Unit  // heartbeat 응답 — 무시
            "subscription.denied" -> {
                Log.w(TAG, "구독 거부: taskRunId=${msg.optString("taskRunId")} reason=${msg.optString("reason")}")
            }
            else -> {
                // 태스크 이벤트 — taskRunId가 있는 경우만 처리
                val taskRunId = msg.optString("taskRunId").ifEmpty {
                    msg.optJSONObject("payload")?.optString("task_run_id") ?: ""
                }
                if (taskRunId.isNotEmpty()) {
                    Log.d(TAG, "태스크 이벤트 수신: type=$type taskRunId=$taskRunId")
                    _events.tryEmit(WsTaskEvent(taskRunId = taskRunId, type = type, raw = msg))
                }
            }
        }
    }

    /** taskRunId 구독 요청. 아직 미인증 상태면 pending 큐에 쌓음. */
    fun subscribeTask(taskRunId: String) {
        if (!authenticated.get() || ws == null) {
            if (!pendingSubscriptions.contains(taskRunId)) pendingSubscriptions.add(taskRunId)
            return
        }
        doSubscribe(taskRunId)
    }

    private fun doSubscribe(taskRunId: String) {
        val socket = ws ?: run {
            if (!pendingSubscriptions.contains(taskRunId)) pendingSubscriptions.add(taskRunId)
            return
        }
        socket.send(
            JSONObject().apply {
                put("type", "subscribe.task")
                put("taskRunId", taskRunId)
            }.toString()
        )
        Log.d(TAG, "구독 요청 전송: taskRunId=$taskRunId")
    }

    fun disconnect() {
        ws?.close(1000, "client disconnect")
        ws = null
        authenticated.set(false)
    }

    fun isConnected() = ws != null && authenticated.get()
}
