package com.example.mob.data.health

import android.app.Activity
import android.content.Context
import android.util.Log
import com.samsung.android.sdk.health.data.HealthDataService
import com.samsung.android.sdk.health.data.HealthDataStore
import com.samsung.android.sdk.health.data.permission.AccessType
import com.samsung.android.sdk.health.data.permission.Permission
import com.samsung.android.sdk.health.data.request.DataType
import com.samsung.android.sdk.health.data.request.DataTypes
import com.samsung.android.sdk.health.data.request.LocalTimeFilter
import com.samsung.android.sdk.health.data.request.Ordering
import java.time.LocalDateTime
import java.time.ZoneId

class SamsungHealthManager(private val context: Context) {

    private var store: HealthDataStore? = null

    val permissions = setOf(
        Permission.of(DataTypes.HEART_RATE, AccessType.READ),
        Permission.of(DataTypes.STEPS, AccessType.READ),
        Permission.of(DataTypes.SLEEP, AccessType.READ),
        Permission.of(DataTypes.BLOOD_OXYGEN, AccessType.READ),
        Permission.of(DataTypes.EXERCISE, AccessType.READ),
    )

    suspend fun connect() {
        Log.d("SamsungHealth", "HealthDataStore 연결 중...")
        store = HealthDataService.getStore(context)
    }

    suspend fun hasAllPermissions(): Boolean {
        val currentStore = store ?: return false
        val granted = currentStore.getGrantedPermissions(permissions)
        return granted.containsAll(permissions)
    }

    suspend fun requestPermissions(activity: Activity): Set<Permission> {
        val currentStore = store ?: return emptySet()
        return currentStore.requestPermissions(permissions, activity)
    }

    suspend fun readLast24Hours(): WatchHealthSnapshot {
        Log.d("SamsungHealth", "최근 24시간 데이터 읽기 시도 중...")
        val currentStore = store ?: error("Samsung Health에 연결되지 않음")
        val endTime = LocalDateTime.now()
        val startTime = endTime.minusHours(24)
        val timeFilter = LocalTimeFilter.of(startTime, endTime)
        val zone = ZoneId.systemDefault()

        // 심박수 (최신 1건 평균값)
        val heartRateData = currentStore.readData(
            DataTypes.HEART_RATE.readDataRequestBuilder
                .setLocalTimeFilter(timeFilter)
                .setOrdering(Ordering.DESC)
                .build()
        ).dataList
        val heartRate = heartRateData.firstOrNull()
            ?.getValue(DataType.HeartRateType.HEART_RATE)?.toInt()

        // 걸음수 합계 (aggregate)
        val stepsData = currentStore.aggregateData(
            DataType.StepsType.TOTAL.requestBuilder
                .setLocalTimeFilter(timeFilter)
                .build()
        ).dataList
        val steps = stepsData.firstOrNull()?.value?.toInt()

        // 수면 (최신 세션)
        val sleepPoint = currentStore.readData(
            DataTypes.SLEEP.readDataRequestBuilder
                .setLocalTimeFilter(timeFilter)
                .setOrdering(Ordering.DESC)
                .build()
        ).dataList.firstOrNull()
        val sleepDuration = sleepPoint?.getValue(DataType.SleepType.DURATION)
        val latestSleepSession = sleepPoint?.getValue(DataType.SleepType.SESSIONS)?.lastOrNull()

        // 혈중 산소 포화도
        val spO2 = currentStore.readData(
            DataTypes.BLOOD_OXYGEN.readDataRequestBuilder
                .setLocalTimeFilter(timeFilter)
                .setOrdering(Ordering.DESC)
                .build()
        ).dataList.firstOrNull()
            ?.getValue(DataType.BloodOxygenType.OXYGEN_SATURATION)?.toDouble()

        // 칼로리 합계 (aggregate)
        val calories = currentStore.aggregateData(
            DataType.ExerciseType.TOTAL_CALORIES.requestBuilder
                .setLocalTimeFilter(timeFilter)
                .build()
        ).dataList.firstOrNull()?.value?.toDouble()


        val snapshot = WatchHealthSnapshot(
            measuredAt = endTime,
            heartRate = heartRate,
            steps = steps,
            sleepDurationMinutes = sleepDuration?.toMinutes()?.toInt(),
            sleepStartAt = latestSleepSession?.startTime?.let { LocalDateTime.ofInstant(it, zone) },
            sleepEndAt = latestSleepSession?.endTime?.let { LocalDateTime.ofInstant(it, zone) },
            spO2 = spO2,
            stressLevel = null,
            caloriesBurned = calories
        )

        Log.d("SamsungHealth", """
            ===== 갤럭시워치 데이터 수집 =====
            측정시각  : ${snapshot.measuredAt}
            심박수    : ${snapshot.heartRate ?: "없음"} bpm
            걸음수    : ${snapshot.steps ?: "없음"} 걸음
            수면시간  : ${snapshot.sleepDurationMinutes ?: "없음"} 분
            수면시작  : ${snapshot.sleepStartAt ?: "없음"}
            수면종료  : ${snapshot.sleepEndAt ?: "없음"}
            산소포화도: ${snapshot.spO2 ?: "없음"} %
            칼로리    : ${snapshot.caloriesBurned ?: "없음"} kcal
            ==================================
        """.trimIndent())

        return snapshot
    }
}
