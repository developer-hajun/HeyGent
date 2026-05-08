package com.ssafy.heygent.domain.iot.entity;

import com.ssafy.heygent.domain.user.entity.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@Table(
    name = "iot_devices",
    uniqueConstraints = {
        @UniqueConstraint(name = "uk_iot_devices_device_id", columnNames = "device_id"),
        @UniqueConstraint(name = "uk_iot_devices_user_id", columnNames = "user_id")
    }
)
@EntityListeners(AuditingEntityListener.class)
public class IotDevice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "device_id", nullable = false, length = 80)
    private String deviceId;

    @Column(name = "display_name", length = 100)
    private String displayName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private IotDeviceStatus status;

    @Column(name = "last_seen_at")
    private LocalDateTime lastSeenAt;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    public boolean isActive() {
        return status == IotDeviceStatus.ACTIVE;
    }

    public void updateStatus(IotDeviceStatus status) {
        this.status = status;
    }

    public void updateDisplayName(String displayName) {
        if (displayName != null) {
            this.displayName = displayName;
        }
    }

    public void markSeen(LocalDateTime seenAt) {
        this.lastSeenAt = seenAt;
    }
}
