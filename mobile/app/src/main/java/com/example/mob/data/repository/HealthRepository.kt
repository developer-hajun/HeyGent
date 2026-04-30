package com.heygents.mob.data.repository

import android.app.Activity
import android.content.Context
import com.example.mob.data.remote.RetrofitClient
import com.heygents.mob.data.health.SamsungHealthManager
import com.heygents.mob.data.health.WatchHealthDataBatchRequest
import com.heygents.mob.data.health.WatchHealthDataItemRequest
import java.time.format.DateTimeFormatter

class HealthRepository(context: Context) {

    private val samsungHealthManager = SamsungHealthManager(context)
    private val apiService = RetrofitClient.healthApiService
    private val formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME

    val permissions = samsungHealthManager.permissions

    suspend fun connect() = samsungHealthManager.connect()

    suspend fun hasAllPermissions(): Boolean = samsungHealthManager.hasAllPermissions()

    suspend fun requestPermissions(activity: Activity) = samsungHealthManager.requestPermissions(activity)

    suspend fun syncToServer(): Result<Unit> = runCatching {
        samsungHealthManager.connect()

        val snapshot = samsungHealthManager.readLast24Hours()

        val item = WatchHealthDataItemRequest(
            measuredAt = snapshot.measuredAt.format(formatter),
            heartRate = snapshot.heartRate,
            steps = snapshot.steps,
            floors = snapshot.floors,
            caloriesBurned = snapshot.caloriesBurned,
            activeCalories = snapshot.activeCalories,
            distance = snapshot.distance,
            activeTimeMinutes = snapshot.activeTimeMinutes,
            sleepDurationMinutes = snapshot.sleepDurationMinutes,
            sleepStartAt = snapshot.sleepStartAt?.format(formatter),
            sleepEndAt = snapshot.sleepEndAt?.format(formatter),
            sleepScore = snapshot.sleepScore,
            spO2 = snapshot.spO2,
            bodyWeight = snapshot.bodyWeight,
            bodyHeight = snapshot.bodyHeight,
            bodyFat = snapshot.bodyFat,
            skeletalMuscle = snapshot.skeletalMuscle,
            waterIntake = snapshot.waterIntake,
            energyScore = snapshot.energyScore,
            bloodPressureSystolic = snapshot.bloodPressureSystolic,
            bloodPressureDiastolic = snapshot.bloodPressureDiastolic,
            bloodGlucose = snapshot.bloodGlucose
        )

        val response = apiService.saveWatchData(WatchHealthDataBatchRequest(items = listOf(item)))
        if (response.status != 200) error("서버 저장 실패: ${response.message}")
    }
}
