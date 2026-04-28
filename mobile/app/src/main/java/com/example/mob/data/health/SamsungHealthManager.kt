package com.example.mob.data.health

import android.app.Activity
import android.content.Context
import com.samsung.android.sdk.healthdata.HealthConnectionErrorResult
import com.samsung.android.sdk.healthdata.HealthDataResolver
import com.samsung.android.sdk.healthdata.HealthDataStore
import com.samsung.android.sdk.healthdata.HealthPermissionManager
import kotlinx.coroutines.suspendCancellableCoroutine
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneId
import kotlin.coroutines.resume

class SamsungHealthManager(private val context: Context) {

    private var store: HealthDataStore? = null

    companion object {
        const val HEART_RATE_TYPE = "com.samsung.health.heart_rate"
        const val STEP_COUNT_TYPE = "com.samsung.health.step_count"
        const val SLEEP_TYPE = "com.samsung.health.sleep"
        const val SPO2_TYPE = "com.samsung.health.oxygen_saturation"
        const val STRESS_TYPE = "com.samsung.health.stress"
        const val EXERCISE_TYPE = "com.samsung.health.exercise"
    }

    val permissionKeys = setOf(
        HealthPermissionManager.PermissionKey(HEART_RATE_TYPE, HealthPermissionManager.PermissionType.READ),
        HealthPermissionManager.PermissionKey(STEP_COUNT_TYPE, HealthPermissionManager.PermissionType.READ),
        HealthPermissionManager.PermissionKey(SLEEP_TYPE, HealthPermissionManager.PermissionType.READ),
        HealthPermissionManager.PermissionKey(SPO2_TYPE, HealthPermissionManager.PermissionType.READ),
        HealthPermissionManager.PermissionKey(STRESS_TYPE, HealthPermissionManager.PermissionType.READ),
        HealthPermissionManager.PermissionKey(EXERCISE_TYPE, HealthPermissionManager.PermissionType.READ),
    )

    suspend fun connect(): Boolean = suspendCancellableCoroutine { cont ->
        val listener = object : HealthDataStore.ConnectionListener {
            override fun onConnected() {
                if (cont.isActive) cont.resume(true)
            }
            override fun onConnectionFailed(error: HealthConnectionErrorResult) {
                if (cont.isActive) cont.resume(false)
            }
            override fun onDisconnected() {}
        }
        store = HealthDataStore(context, listener)
        store?.connectService()
        cont.invokeOnCancellation { store?.disconnectService() }
    }

    fun disconnect() {
        store?.disconnectService()
        store = null
    }

    fun hasAllPermissions(): Boolean {
        val currentStore = store ?: return false
        return HealthPermissionManager(currentStore).isPermissionAcquired(permissionKeys)
    }

    fun requestPermissions(activity: Activity) {
        val currentStore = store ?: return
        HealthPermissionManager(currentStore)
            .requestPermissions(permissionKeys, activity)
            .setResultListener { /* 결과는 Activity의 onActivityResult에서 처리 */ }
    }

    suspend fun readLast24Hours(): WatchHealthSnapshot {
        val endTime = System.currentTimeMillis()
        val startTime = endTime - 24 * 60 * 60 * 1000L
        val resolver = HealthDataResolver(store ?: error("Samsung Health에 연결되지 않음"), null)

        val sleep = readSleep(resolver, startTime, endTime)

        return WatchHealthSnapshot(
            measuredAt = LocalDateTime.now(),
            heartRate = readHeartRate(resolver, startTime, endTime),
            steps = readSteps(resolver, startTime, endTime),
            sleepDurationMinutes = sleep?.durationMinutes,
            sleepStartAt = sleep?.startAt,
            sleepEndAt = sleep?.endAt,
            spO2 = readSpO2(resolver, startTime, endTime),
            stressLevel = readStress(resolver, startTime, endTime),
            caloriesBurned = readCalories(resolver, startTime, endTime)
        )
    }

    private suspend fun readHeartRate(resolver: HealthDataResolver, startTime: Long, endTime: Long): Int? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(HEART_RATE_TYPE)
                .setProperties(arrayOf("heart_rate", "start_time"))
                .setFilter(timeFilter(startTime, endTime))
                .setSort("start_time", HealthDataResolver.SortOrder.DESC)
                .build()
            resolver.read(request).setResultListener { result ->
                val value = if (result.iterator().hasNext())
                    result.iterator().next().getFloat("heart_rate").toInt()
                else null
                result.close()
                if (cont.isActive) cont.resume(value)
            }
        }

    private suspend fun readSteps(resolver: HealthDataResolver, startTime: Long, endTime: Long): Int? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(STEP_COUNT_TYPE)
                .setProperties(arrayOf("count"))
                .setFilter(timeFilter(startTime, endTime))
                .build()
            resolver.read(request).setResultListener { result ->
                var total = 0
                val iterator = result.iterator()
                while (iterator.hasNext()) total += iterator.next().getInt("count")
                result.close()
                if (cont.isActive) cont.resume(if (total == 0) null else total)
            }
        }

    private suspend fun readSleep(resolver: HealthDataResolver, startTime: Long, endTime: Long): SleepInfo? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(SLEEP_TYPE)
                .setProperties(arrayOf("start_time", "end_time"))
                .setFilter(timeFilter(startTime, endTime))
                .setSort("start_time", HealthDataResolver.SortOrder.DESC)
                .build()
            resolver.read(request).setResultListener { result ->
                val info = if (result.iterator().hasNext()) {
                    val data = result.iterator().next()
                    val start = data.getLong("start_time")
                    val end = data.getLong("end_time")
                    val zone = ZoneId.systemDefault()
                    SleepInfo(
                        durationMinutes = ((end - start) / 60_000L).toInt(),
                        startAt = LocalDateTime.ofInstant(Instant.ofEpochMilli(start), zone),
                        endAt = LocalDateTime.ofInstant(Instant.ofEpochMilli(end), zone)
                    )
                } else null
                result.close()
                if (cont.isActive) cont.resume(info)
            }
        }

    private suspend fun readSpO2(resolver: HealthDataResolver, startTime: Long, endTime: Long): Double? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(SPO2_TYPE)
                .setProperties(arrayOf("spo2", "start_time"))
                .setFilter(timeFilter(startTime, endTime))
                .setSort("start_time", HealthDataResolver.SortOrder.DESC)
                .build()
            resolver.read(request).setResultListener { result ->
                val value = if (result.iterator().hasNext())
                    result.iterator().next().getFloat("spo2").toDouble()
                else null
                result.close()
                if (cont.isActive) cont.resume(value)
            }
        }

    private suspend fun readStress(resolver: HealthDataResolver, startTime: Long, endTime: Long): Int? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(STRESS_TYPE)
                .setProperties(arrayOf("stress_score", "start_time"))
                .setFilter(timeFilter(startTime, endTime))
                .setSort("start_time", HealthDataResolver.SortOrder.DESC)
                .build()
            resolver.read(request).setResultListener { result ->
                val value = if (result.iterator().hasNext())
                    result.iterator().next().getInt("stress_score")
                else null
                result.close()
                if (cont.isActive) cont.resume(value)
            }
        }

    private suspend fun readCalories(resolver: HealthDataResolver, startTime: Long, endTime: Long): Double? =
        suspendCancellableCoroutine { cont ->
            val request = HealthDataResolver.ReadRequest.Builder()
                .setDataType(EXERCISE_TYPE)
                .setProperties(arrayOf("calorie"))
                .setFilter(timeFilter(startTime, endTime))
                .build()
            resolver.read(request).setResultListener { result ->
                var total = 0.0
                val iterator = result.iterator()
                while (iterator.hasNext()) total += iterator.next().getDouble("calorie")
                result.close()
                if (cont.isActive) cont.resume(if (total == 0.0) null else total)
            }
        }

    private fun timeFilter(startTime: Long, endTime: Long) = HealthDataResolver.Filter.and(
        HealthDataResolver.Filter.greaterThanEquals("start_time", startTime),
        HealthDataResolver.Filter.lessThan("start_time", endTime)
    )

    private data class SleepInfo(
        val durationMinutes: Int,
        val startAt: LocalDateTime,
        val endAt: LocalDateTime
    )
}
