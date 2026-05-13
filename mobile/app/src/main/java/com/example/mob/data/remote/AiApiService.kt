package com.example.mob.data.remote

import com.google.gson.JsonObject
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

data class OpenAiProvider(
    val providerName: String,
    val authType: String,
    val connected: Boolean,
    val available: Boolean,
    val expiresAt: String?,
    val status: String,
)

data class OpenAiProvidersResponse(
    val providers: List<OpenAiProvider>,
)

data class OpenAiModelsResponse(
    val defaultModel: String,
    val models: List<String>,
)

data class OpenAiUsageResponse(
    val providerName: String,
    val usage: JsonObject,
    val costs: JsonObject,
)

interface AiApiService {

    @GET("api/v1/ai/openai/providers")
    suspend fun getOpenAiProviders(): ServerResponse<OpenAiProvidersResponse>

    @GET("api/v1/ai/openai/models")
    suspend fun getOpenAiModels(): ServerResponse<OpenAiModelsResponse>

    @GET("api/v1/ai/openai/usages/me")
    suspend fun getOpenAiUsage(
        @Query("providerName") providerName: String,
        @Query("from") from: String? = null,
        @Query("to") to: String? = null,
    ): ServerResponse<OpenAiUsageResponse>

    @GET("ai/api/v1/sessions")
    suspend fun getChatSessions(
        @Query("page") page: Int = 1,
        @Query("pageSize") pageSize: Int = 20,
    ): ChatSessionListResponse

    @GET("ai/api/v1/sessions/{sessionId}/messages")
    suspend fun getChatSessionMessages(
        @Path("sessionId") sessionId: String,
        @Query("limit") limit: Int = 100,
    ): ChatSessionMessagesResponse

    @POST("ai/api/v1/sessions/messages")
    suspend fun sendChatMessageNewSession(
        @Body request: SendChatMessageRequest,
    ): SendChatMessageResponse

    @POST("ai/api/v1/sessions/{sessionId}/messages")
    suspend fun sendChatMessage(
        @Path("sessionId") sessionId: String,
        @Body request: SendChatMessageRequest,
    ): SendChatMessageResponse
}
