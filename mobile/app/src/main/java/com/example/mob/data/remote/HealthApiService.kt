package com.example.mob.data.remote

import com.example.mob.data.health.WatchHealthDataBatchRequest
import com.example.mob.data.health.WatchHealthDataResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

data class ServerResponse<T>(
    val status: Int,
    val message: String,
    val data: T?
)

interface HealthApiService {

    @POST("api/v1/health/watch")
    suspend fun saveWatchData(
        @Body request: WatchHealthDataBatchRequest
    ): ServerResponse<List<WatchHealthDataResponse>>

    @GET("api/v1/health/watch")
    suspend fun getMyWatchData(): ServerResponse<List<WatchHealthDataResponse>>
}
