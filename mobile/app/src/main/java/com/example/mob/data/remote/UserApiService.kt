package com.example.mob.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH

data class UpdateUserRequest(
    val nickname: String? = null,
    val profileImage: String? = null,
)

data class UserResponse(
    val id: Long,
    val kakaoId: Long,
    val nickname: String?,
    val profileImage: String?,
    val createdAt: String?,
    val updatedAt: String?,
)

interface UserApiService {

    @GET("api/v1/users/me")
    suspend fun getMe(): ServerResponse<UserResponse>

    @PATCH("api/v1/users/me")
    suspend fun updateMe(
        @Body request: UpdateUserRequest,
    ): ServerResponse<UserResponse>
}
