package com.ssafy.heygent.domain.health.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.ssafy.heygent.domain.health.entity.MeasurementLog;
import lombok.*;

import java.time.LocalDateTime;

@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@JsonInclude(JsonInclude.Include.NON_NULL)
public class HealthSummaryResponseDto {

    private LocalDateTime measuredAt;

    // 활동
    private Integer stepCount;
    private Integer activeMinutes;
    private Double totalCalories;
    private Double activeCalories;

    // 체성분
    private Double heightCm;
    private Double weightKg;
    private Double bodyFatPct;
    private Double muscleMassKg;

    // 활력
    private Integer heartRateBpm;
    private Double systolicBp;
    private Double diastolicBp;

    // 수면
    private Integer durationMinutes;
    private Integer sleepScore;

    public static HealthSummaryResponseDto from(MeasurementLog log) {
        var builder = HealthSummaryResponseDto.builder()
                .measuredAt(log.getMeasuredAt());

        if (log.getDailyActivity() != null) {
            var a = log.getDailyActivity();
            builder.stepCount(a.getStepCount())
                    .activeMinutes(a.getActiveMinutes())
                    .totalCalories(a.getTotalCalories())
                    .activeCalories(a.getActiveCalories());
        }

        if (log.getPhysicalProfile() != null) {
            var p = log.getPhysicalProfile();
            builder.heightCm(p.getHeightCm())
                    .weightKg(p.getWeightKg())
                    .bodyFatPct(p.getBodyFatPct())
                    .muscleMassKg(p.getMuscleMassKg());
        }

        if (log.getVitalLog() != null) {
            var v = log.getVitalLog();
            builder.heartRateBpm(v.getHeartRateBpm())
                    .systolicBp(v.getSystolicBp())
                    .diastolicBp(v.getDiastolicBp());
        }

        if (log.getSleepRecord() != null) {
            var s = log.getSleepRecord();
            builder.durationMinutes(s.getDurationMinutes())
                    .sleepScore(s.getSleepScore());
        }

        return builder.build();
    }
}
