package com.ssafy.heygent.domain.health.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "vital_logs")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
public class VitalLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long vitalId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "log_id")
    private MeasurementLog measurementLog;

    private Integer heartRateBpm;
    private Double systolicBp;
    private Double diastolicBp;
}