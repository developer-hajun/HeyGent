package com.example.mob.data.repository

import android.app.Activity
import android.content.Context
import com.example.mob.data.health.SamsungHealthManager
import com.example.mob.data.health.WatchHealthDataBatchRequest
import com.example.mob.data.health.WatchHealthDataItemRequest
import com.example.mob.data.remote.RetrofitClient
import java.time.format.DateTimeFormatter

class HealthRepository(context: Context) {

    private val samsungHealthManager = SamsungHealthManager(context)
    private val apiService = RetrofitClient.healthApiService
    private val formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME

    val permissionKeys = samsungHealthManager.permissionKeys

    suspend fun connect(): Boolean = samsungHealthManager.connect()

    fun disconnect() = samsungHealthManager.disconnect()

    fun hasAllPermissions(): Boolean = samsungHealthManager.hasAllPermissions()

    fun requestPermissions(activity: Activity) = samsungHealthManager.requestPermissions(activity)

    suspend fun syncToServer(): Result<Unit> = runCatching {
        check(samsungHealthManager.connect()) { "Samsung Health 연결 실패. Samsung Health 앱이 설치되어 있는지 확인하세요." }

        try {
            val snapshot = samsungHealthManager.readLast24Hours()

            val item = WatchHealthDataItemRequest(
                measuredAt = snapshot.measuredAt.format(formatter),
                heartRate = snapshot.heartRate,
                steps = snapshot.steps,
                sleepDurationMinutes = snapshot.sleepDurationMinutes,
                sleepStartAt = snapshot.sleepStartAt?.format(formatter),
                sleepEndAt = snapshot.sleepEndAt?.format(formatter),
                spO2 = snapshot.spO2,
                stressLevel = snapshot.stressLevel,
                caloriesBurned = snapshot.caloriesBurned
            )

            val response = apiService.saveWatchData(WatchHealthDataBatchRequest(items = listOf(item)))
            if (response.status != 200) error("서버 저장 실패: ${response.message}")
        } finally {
            samsungHealthManager.disconnect()
        }
    }
}
