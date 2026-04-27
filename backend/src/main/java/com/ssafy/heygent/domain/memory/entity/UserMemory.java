package com.ssafy.heygent.domain.memory.entity;

import java.time.LocalDateTime;
import java.util.Map;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@Table(name = "user_memories")
@EntityListeners(AuditingEntityListener.class)
public class UserMemory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(length = 30)
    private MemoryStoreType storeType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 50)
    private MemoryType memoryType;

    @Enumerated(EnumType.STRING)
    @Column(length = 30)
    private MemoryScopeType scopeType;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(length = 500)
    private String summary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @Column(columnDefinition = "TEXT")
    private String embeddingText;

    @Column(nullable = false)
    private Double importance;

    @Column(nullable = false)
    private Double confidence;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private MemoryStatus status;

    @Column(length = 100)
    private String sourceSessionKey;

    @Column(length = 100)
    private String sourceTaskRunId;

    @Column(length = 100)
    private String sourceMessageId;

    @Column(columnDefinition = "TEXT")
    private String evidence;

    @Column(length = 500)
    private String updateReason;

    private Long supersededByMemoryId;

    private LocalDateTime validFrom;

    private LocalDateTime validUntil;

    private LocalDateTime invalidatedAt;

    private LocalDateTime expiresAt;

    @Builder.Default
    private Long accessCount = 0L;

    @Builder.Default
    private Long usedCount = 0L;

    private LocalDateTime lastUsedAt;

    @Builder.Default
    private Double usefulnessScore = 0.0;

    private LocalDateTime lastAccessedAt;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    public void delete() {
        this.status = MemoryStatus.DELETED;
    }

    public void markAccessed(LocalDateTime accessedAt) {
        this.lastAccessedAt = accessedAt;
        this.accessCount = safeCount(this.accessCount) + 1;
    }

    public void markUsed(LocalDateTime usedAt, Double usefulnessScore) {
        long previousUsedCount = safeCount(this.usedCount);
        this.lastUsedAt = usedAt;
        this.usedCount = previousUsedCount + 1;

        if (usefulnessScore != null) {
            double previousScore = this.usefulnessScore == null ? 0.0 : this.usefulnessScore;
            this.usefulnessScore = ((previousScore * previousUsedCount) + usefulnessScore) / this.usedCount;
        }
    }

    public void invalidate(Long supersededByMemoryId, String updateReason, LocalDateTime invalidatedAt) {
        this.status = MemoryStatus.INACTIVE;
        this.supersededByMemoryId = supersededByMemoryId;
        this.updateReason = updateReason;
        this.invalidatedAt = invalidatedAt;
        this.validUntil = invalidatedAt;
    }

    private long safeCount(Long value) {
        if (value == null) {
            return 0L;
        }
        return value;
    }
}
