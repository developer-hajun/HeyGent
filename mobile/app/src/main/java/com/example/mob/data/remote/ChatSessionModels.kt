package com.example.mob.data.remote

import com.google.gson.annotations.SerializedName

data class ChatSessionResponse(
    @SerializedName("sessionId") val sessionId: String,
    @SerializedName("title") val title: String?,
    @SerializedName("messageCount") val messageCount: Int = 0,
    @SerializedName("updatedAt") val updatedAt: String?,
    @SerializedName("createdAt") val createdAt: String?,
)

data class ChatSessionListResponse(
    @SerializedName("items") val items: List<ChatSessionResponse>,
    @SerializedName("totalCount") val totalCount: Int,
    @SerializedName("hasNext") val hasNext: Boolean,
)

data class ChatSessionMessageResponse(
    @SerializedName("id") val id: Int,
    @SerializedName("sessionId") val sessionId: String,
    @SerializedName("role") val role: String,
    @SerializedName("content") val content: String?,
    @SerializedName("timestamp") val timestamp: String?,
)

data class ChatSessionMessagesResponse(
    @SerializedName("sessionId") val sessionId: String,
    @SerializedName("totalCount") val totalCount: Int,
    @SerializedName("items") val items: List<ChatSessionMessageResponse>,
)

data class SendChatMessageRequest(
    @SerializedName("content") val content: String,
    @SerializedName("sessionId") val sessionId: String? = null,
    @SerializedName("model") val model: String? = null,
    @SerializedName("intentType") val intentType: String = "agent.loop",
)

data class SendChatMessageResponse(
    @SerializedName("sessionId") val sessionId: String,
    @SerializedName("taskRunId") val taskRunId: String,
    @SerializedName("status") val status: String,
    @SerializedName("userMessage") val userMessage: ChatSessionMessageResponse?,
    @SerializedName("assistantMessage") val assistantMessage: ChatSessionMessageResponse?,
)
