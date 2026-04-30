package com.ssafy.heygent.domain.health.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "physical_profiles")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
public class PhysicalProfile {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long profileId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "log_id")
    private MeasurementLog measurementLog;

    private Double heightCm;
    private Double weightKg;
    private Double bodyFatPct;
    private Double muscleMassKg;
}