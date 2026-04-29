package com.ssafy.heygent.domain.health.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "daily_activities")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
public class DailyActivity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long activityId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "log_id")
    private MeasurementLog measurementLog;

    private Integer stepCount;
    private Integer activeMinutes;
    private Double totalCalories;
    private Double activeCalories;
}