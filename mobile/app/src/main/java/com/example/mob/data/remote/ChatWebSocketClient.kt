package com.example.mob.data.remote

import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class ChatWebSocketClient(
    private val baseUrl: String,
    private val accessToken: String,
    private val onMessageCreated: (ChatSessionMessageResponse) -> Unit,
    private val onConnected: () -> Unit = {},
    private val onDisconnected: () -> Unit = {},
) {
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var isAuthed = false
    private var pendingSessionId: String? = null

    fun connect() {
        val wsUrl = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .trimEnd('/') + "/ai/api/v1/realtime/user/ws"

        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, listener)
    }

    fun subscribeToSession(sessionId: String) {
        if (!isAuthed) {
            pendingSessionId = sessionId
            return
        }
        send(mapOf("type" to "subscribe.session", "sessionId" to sessionId))
    }

    fun disconnect() {
        isAuthed = false
        pendingSessionId = null
        webSocket?.close(1000, "leaving")
        webSocket = null
    }

    private fun send(payload: Map<String, Any?>) {
        webSocket?.send(gson.toJson(payload))
    }

    private val listener = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.d(TAG, "WebSocket connected")
            send(mapOf("type" to "auth.start", "payload" to mapOf("accessToken" to accessToken)))
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            Log.d(TAG, "WS message: $text")
            val type = object : TypeToken<Map<String, Any?>>() {}.type
            val msg: Map<String, Any?> = try {
                gson.fromJson(text, type)
            } catch (_: Exception) {
                return
            }
            when (msg["type"]) {
                "auth.ok" -> {
                    isAuthed = true
                    onConnected()
                    pendingSessionId?.let { subscribeToSession(it) }
                    pendingSessionId = null
                }
                "auth.failed", "auth.timeout" -> {
                    Log.w(TAG, "WS auth failed: ${msg["type"]}")
                    disconnect()
                }
                "session.message.created" -> {
                    val messageMap = msg["message"] ?: return
                    try {
                        val messageJson = gson.toJson(messageMap)
                        val message = gson.fromJson(messageJson, ChatSessionMessageResponse::class.java)
                        onMessageCreated(message)
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse session.message.created", e)
                    }
                }
                "pong" -> Log.v(TAG, "WS pong")
            }
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            webSocket.close(1000, null)
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.d(TAG, "WebSocket closed: $code")
            isAuthed = false
            onDisconnected()
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e(TAG, "WebSocket error", t)
            isAuthed = false
            onDisconnected()
        }
    }

    companion object {
        private const val TAG = "ChatWsClient"
    }
}
