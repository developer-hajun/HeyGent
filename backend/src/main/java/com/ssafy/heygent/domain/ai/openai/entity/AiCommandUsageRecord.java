package com.ssafy.heygent.domain.ai.openai.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
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
@Table(
    name = "ai_command_usage_records",
    indexes = {
        @Index(name = "idx_ai_command_usage_user_created", columnList = "user_id, created_at"),
        @Index(name = "idx_ai_command_usage_user_task", columnList = "user_id, task_run_id"),
        @Index(name = "idx_ai_command_usage_user_session", columnList = "user_id, session_id")
    },
    uniqueConstraints = {
        @UniqueConstraint(name = "uk_ai_command_usage_user_request", columnNames = {"user_id", "request_id"})
    }
)
@EntityListeners(AuditingEntityListener.class)
public class AiCommandUsageRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "provider_name", nullable = false, length = 50)
    private String providerName;

    @Column(nullable = false, length = 100)
    private String model;

    @Column(name = "task_run_id", nullable = false, length = 100)
    private String taskRunId;

    @Column(name = "step_run_id", length = 100)
    private String stepRunId;

    @Column(name = "session_id", length = 100)
    private String sessionId;

    @Column(name = "request_id", length = 100)
    private String requestId;

    @Column(name = "input_tokens", nullable = false)
    private Long inputTokens;

    @Column(name = "output_tokens", nullable = false)
    private Long outputTokens;

    @Column(name = "total_tokens", nullable = false)
    private Long totalTokens;

    @Column(name = "cached_input_tokens")
    private Long cachedInputTokens;

    @Column(name = "reasoning_tokens")
    private Long reasoningTokens;

    @Column(name = "estimated_cost_usd", precision = 20, scale = 10)
    private BigDecimal estimatedCostUsd;

    @Column(nullable = false, length = 10)
    private String currency;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
