package com.example.mob.data.remote

import com.example.mob.BuildConfig
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.MutableSharedFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

    private val BASE_URL = BuildConfig.BASE_URL

    private var accessToken: String = ""
    private var refreshToken: String = ""
    private val tokenLock = Any()

    // 세션 만료 시 UI에 알리기 위한 이벤트 (MainApp에서 collect)
    val sessionExpiredEvent = MutableSharedFlow<Unit>(extraBufferCapacity = 1)

    fun setToken(token: String) { accessToken = token }
    fun setRefreshToken(token: String) { refreshToken = token }
    fun getRefreshToken(): String = refreshToken
    fun clearTokens() { accessToken = ""; refreshToken = "" }

    // Authenticator 전용 클라이언트 — 인터셉터/재시도 없이 refresh 호출만 담당
    private val plainClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()

    private val okHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor { chain ->
                val builder = chain.request().newBuilder()
                if (accessToken.isNotBlank()) {
                    builder.addHeader("Authorization", "Bearer $accessToken")
                }
                chain.proceed(builder.build())
            }
            .authenticator { _, response ->
                // refresh 엔드포인트 자체가 401이면 무한루프 방지
                if (response.request.url.pathSegments.contains("refresh")) return@authenticator null

                synchronized(tokenLock) {
                    val token = refreshToken
                    if (token.isBlank()) {
                        clearTokens()
                        sessionExpiredEvent.tryEmit(Unit)
                        return@synchronized null
                    }

                    try {
                        val refreshRequest = Request.Builder()
                            .url("${BASE_URL}api/v1/auth/refresh")
                            .post(ByteArray(0).toRequestBody(null))
                            .addHeader("Refresh-Token", token)
                            .build()

                        val refreshResponse = plainClient.newCall(refreshRequest).execute()
                        if (refreshResponse.isSuccessful) {
                            val body = refreshResponse.body?.string()
                                ?: return@synchronized null
                            val type = object : TypeToken<ServerResponse<AuthTokens>>() {}.type
                            val serverResp: ServerResponse<AuthTokens> = gson.fromJson(body, type)
                            if (serverResp.status == 200 && serverResp.data != null) {
                                accessToken = serverResp.data.accessToken
                                refreshToken = serverResp.data.refreshToken
                                return@synchronized response.request.newBuilder()
                                    .removeHeader("Authorization")
                                    .addHeader("Authorization", "Bearer $accessToken")
                                    .build()
                            }
                        }
                    } catch (_: Exception) { }

                    clearTokens()
                    sessionExpiredEvent.tryEmit(Unit)
                    null
                }
            }
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BODY
                }
            )
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val authApiService: AuthApiService by lazy {
        retrofit.create(AuthApiService::class.java)
    }

    val healthApiService: HealthApiService by lazy {
        retrofit.create(HealthApiService::class.java)
    }

    val userApiService: UserApiService by lazy {
        retrofit.create(UserApiService::class.java)
    }

    val aiApiService: AiApiService by lazy {
        retrofit.create(AiApiService::class.java)
    }
}
