package com.example.mob.data.remote

import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

data class KakaoLoginRequest(val accessToken: String)

data class AuthTokens(
    val accessToken: String,
    val refreshToken: String,
)

interface AuthApiService {

    @POST("api/v1/auth/kakao/mobile")
    suspend fun kakaoLogin(
        @Body request: KakaoLoginRequest,
    ): ServerResponse<AuthTokens>

    @POST("api/v1/auth/logout")
    suspend fun logout(
        @Header("Refresh-Token") refreshToken: String,
    ): ServerResponse<Unit>

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(
        @Header("Refresh-Token") refreshToken: String,
    ): ServerResponse<AuthTokens>
}
