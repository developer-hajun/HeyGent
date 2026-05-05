package com.ssafy.heygent.domain.health.entity;

import com.ssafy.heygent.domain.user.entity.User;
import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "measurement_logs")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
public class MeasurementLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long logId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    private LocalDateTime measuredAt;

    @Enumerated(EnumType.STRING)
    private LogCategory category;

    @OneToOne(mappedBy = "measurementLog", cascade = CascadeType.ALL)
    private DailyActivity dailyActivity;

    @OneToOne(mappedBy = "measurementLog", cascade = CascadeType.ALL)
    private PhysicalProfile physicalProfile;

    @OneToOne(mappedBy = "measurementLog", cascade = CascadeType.ALL)
    private VitalLog vitalLog;

    @OneToOne(mappedBy = "measurementLog", cascade = CascadeType.ALL)
    private SleepRecord sleepRecord;

    public void setDetails(DailyActivity activity, PhysicalProfile profile, VitalLog vital, SleepRecord sleep) {
        this.dailyActivity = activity;
        this.physicalProfile = profile;
        this.vitalLog = vital;
        this.sleepRecord = sleep;
    }
}

