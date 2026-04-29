package com.example.mob.data.health

import java.time.LocalDateTime

data class WatchHealthSnapshot(
    val measuredAt: LocalDateTime,
    // 기본 지표
    val heartRate: Int?,
    val steps: Int?,
    val floors: Int?,
    val caloriesBurned: Double?, // 총 소모 칼로리
    val activeCalories: Double?, // 활동 소모 칼로리
    val distance: Double?,       // 이동 거리(m)
    val activeTimeMinutes: Int?, // 활동 시간
    
    // 수면 상세
    val sleepDurationMinutes: Int?,
    val sleepStartAt: LocalDateTime?,
    val sleepEndAt: LocalDateTime?,
    val sleepScore: Int?,
    
    // 신체 구성 및 기타
    val spO2: Double?,
    val bodyWeight: Double?,
    val bodyHeight: Double?,
    val bodyFat: Double?,
    val skeletalMuscle: Double?,
    val waterIntake: Double?,    // 음수량(ml)
    val energyScore: Int?,       // 삼성 AI 에너지 점수
    
    // 혈관 건강
    val bloodPressureSystolic: Double?,
    val bloodPressureDiastolic: Double?,
    val bloodGlucose: Double?
)

data class WatchHealthDataItemRequest(
    val measuredAt: String,
    val heartRate: Int?,
    val steps: Int?,
    val floors: Int?,
    val caloriesBurned: Double?,
    val activeCalories: Double?,
    val distance: Double?,
    val activeTimeMinutes: Int?,
    val sleepDurationMinutes: Int?,
    val sleepStartAt: String?,
    val sleepEndAt: String?,
    val sleepScore: Int?,
    val spO2: Double?,
    val bodyWeight: Double?,
    val bodyHeight: Double?,
    val bodyFat: Double?,
    val skeletalMuscle: Double?,
    val waterIntake: Double?,
    val energyScore: Int?,
    val bloodPressureSystolic: Double?,
    val bloodPressureDiastolic: Double?,
    val bloodGlucose: Double?
)

data class WatchHealthDataBatchRequest(
    val items: List<WatchHealthDataItemRequest>
)

data class WatchHealthDataResponse(
    val status: Int,
    val message: String
)
