package com.ssafy.heygent.domain.bridge.entity;

import com.ssafy.heygent.domain.user.entity.User;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
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
    name = "bridge_devices",
    uniqueConstraints = {
        @UniqueConstraint(name = "uk_bridge_devices_token_hash", columnNames = "token_hash")
    },
    indexes = {
        @Index(name = "idx_bridge_devices_user_id", columnList = "user_id"),
        @Index(name = "idx_bridge_devices_user_active", columnList = "user_id,revoked_at")
    }
)
@EntityListeners(AuditingEntityListener.class)
public class BridgeDevice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "device_name", nullable = false, length = 60)
    private String deviceName;

    @Column(name = "token_hash", nullable = false, length = 64)
    private String tokenHash;

    @Column(name = "last_seen_at")
    private LocalDateTime lastSeenAt;

    @Column(name = "revoked_at")
    private LocalDateTime revokedAt;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    public boolean isActive() {
        return revokedAt == null;
    }

    public void revoke(LocalDateTime revokedAt) {
        this.revokedAt = revokedAt;
    }

    public void markSeen(LocalDateTime seenAt) {
        this.lastSeenAt = seenAt;
    }

    public void renameTo(String deviceName) {
        if (deviceName != null && !deviceName.isBlank()) {
            this.deviceName = deviceName;
        }
    }
}
