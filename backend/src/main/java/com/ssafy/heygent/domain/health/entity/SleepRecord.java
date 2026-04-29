package com.ssafy.heygent.domain.health.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "sleep_records")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
public class SleepRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long sleepId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "log_id")
    private MeasurementLog measurementLog;

    private Integer durationMinutes;
    private Integer sleepScore;
}