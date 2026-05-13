package com.example.mob.feature.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.mob.data.remote.ChatSessionMessageResponse
import com.example.mob.data.remote.ChatSessionResponse
import com.example.mob.data.remote.RetrofitClient
import com.example.mob.data.remote.SendChatMessageRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

class ChatViewModel : ViewModel() {

    private val _sessions = MutableStateFlow<List<ChatSessionResponse>>(emptyList())
    val sessions: StateFlow<List<ChatSessionResponse>> = _sessions.asStateFlow()

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _isLoadingSessions = MutableStateFlow(false)
    val isLoadingSessions: StateFlow<Boolean> = _isLoadingSessions.asStateFlow()

    private val _isProcessing = MutableStateFlow(false)
    val isProcessing: StateFlow<Boolean> = _isProcessing.asStateFlow()

    private val _activeSessionId = MutableStateFlow<String?>(null)
    val activeSessionId: StateFlow<String?> = _activeSessionId.asStateFlow()

    fun loadSessions() {
        viewModelScope.launch {
            _isLoadingSessions.value = true
            try {
                val resp = RetrofitClient.aiApiService.getChatSessions()
                if (resp.status == 200) _sessions.value = resp.data?.items ?: emptyList()
            } catch (_: Exception) {}
            _isLoadingSessions.value = false
        }
    }

    fun openSession(sessionId: String) {
        _activeSessionId.value = sessionId
        _messages.value = emptyList()
        viewModelScope.launch {
            try {
                val resp = RetrofitClient.aiApiService.getChatSessionMessages(sessionId)
                if (resp.status == 200) {
                    _messages.value = resp.data?.items?.mapNotNull { it.toChatMessage() } ?: emptyList()
                }
            } catch (_: Exception) {}
        }
    }

    fun startNewSession() {
        _activeSessionId.value = null
        _messages.value = emptyList()
    }

    fun sendMessage(content: String) {
        val currentSessionId = _activeSessionId.value
        viewModelScope.launch {
            _isProcessing.value = true
            _messages.value = _messages.value + ChatMessage(
                isBot = false, text = content, timestamp = nowFormatted()
            )
            try {
                val request = SendChatMessageRequest(content = content, sessionId = currentSessionId)
                val resp = if (currentSessionId != null) {
                    RetrofitClient.aiApiService.sendChatMessage(currentSessionId, request)
                } else {
                    RetrofitClient.aiApiService.sendChatMessageNewSession(request)
                }
                if (resp.status == 200 && resp.data != null) {
                    if (_activeSessionId.value == null) _activeSessionId.value = resp.data.sessionId
                    resp.data.assistantMessage?.toChatMessage()?.let {
                        _messages.value = _messages.value + it
                    }
                    loadSessions()
                }
            } catch (_: Exception) {}
            _isProcessing.value = false
        }
    }

    fun stopProcessing() {
        _isProcessing.value = false
    }
}

private fun nowFormatted() = SimpleDateFormat("a\nhh:mm", Locale.KOREAN).format(Date())

private fun ChatSessionMessageResponse.toChatMessage(): ChatMessage? {
    val text = content?.takeIf { it.isNotEmpty() } ?: return null
    val time = try {
        val millis = java.time.OffsetDateTime.parse(timestamp).toInstant().toEpochMilli()
        SimpleDateFormat("a\nhh:mm", Locale.KOREAN).format(Date(millis))
    } catch (_: Exception) { timestamp ?: "" }
    return ChatMessage(isBot = role == "assistant", text = text, timestamp = time)
}

fun ChatSessionResponse.formatTime(): String {
    val ts = updatedAt ?: createdAt ?: return ""
    return try {
        val millis = java.time.OffsetDateTime.parse(ts).toInstant().toEpochMilli()
        val msgDate = Date(millis)
        val cal = Calendar.getInstance().apply { time = msgDate }
        val now = Calendar.getInstance()
        when {
            cal[Calendar.YEAR] == now[Calendar.YEAR] &&
                    cal[Calendar.DAY_OF_YEAR] == now[Calendar.DAY_OF_YEAR] ->
                SimpleDateFormat("a h:mm", Locale.KOREAN).format(msgDate)
            cal[Calendar.YEAR] == now[Calendar.YEAR] &&
                    now[Calendar.DAY_OF_YEAR] - cal[Calendar.DAY_OF_YEAR] == 1 -> "어제"
            else -> SimpleDateFormat("M월 d일", Locale.KOREAN).format(msgDate)
        }
    } catch (_: Exception) { "" }
}
