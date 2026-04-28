package com.example.mob.data.health

import java.time.LocalDateTime

data class WatchHealthSnapshot(
    val measuredAt: LocalDateTime,
    val heartRate: Int?,
    val steps: Int?,
    val sleepDurationMinutes: Int?,
    val sleepStartAt: LocalDateTime?,
    val sleepEndAt: LocalDateTime?,
    val spO2: Double?,
    val stressLevel: Int?,
    val caloriesBurned: Double?
)

data class WatchHealthDataItemRequest(
    val measuredAt: String,
    val heartRate: Int?,
    val steps: Int?,
    val sleepDurationMinutes: Int?,
    val sleepStartAt: String?,
    val sleepEndAt: String?,
    val spO2: Double?,
    val stressLevel: Int?,
    val caloriesBurned: Double?
)

data class WatchHealthDataBatchRequest(
    val items: List<WatchHealthDataItemRequest>
)

data class WatchHealthDataResponse(
    val id: Long,
    val userId: Long,
    val measuredAt: String,
    val heartRate: Int?,
    val steps: Int?,
    val sleepDurationMinutes: Int?,
    val sleepStartAt: String?,
    val sleepEndAt: String?,
    val spO2: Double?,
    val stressLevel: Int?,
    val caloriesBurned: Double?,
    val createdAt: String
)
