package com.ssafy.heygent.domain.ai.openai.entity;

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
    name = "ai_token_usage_logs",
    indexes = {
        @Index(name = "idx_ai_token_usage_logs_user_created", columnList = "user_id, created_at"),
        @Index(name = "idx_ai_token_usage_logs_task", columnList = "task_run_id")
    }
)
@EntityListeners(AuditingEntityListener.class)
public class AiTokenUsageLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "task_run_id", length = 100)
    private String taskRunId;

    @Column(name = "step_run_id", length = 100)
    private String stepRunId;

    @Column(name = "provider_name", nullable = false, length = 50)
    private String providerName;

    @Column(name = "auth_type", nullable = false, length = 30)
    private String authType;

    @Column(nullable = false, length = 100)
    private String model;

    @Column(name = "response_id", length = 100)
    private String responseId;

    @Column(name = "input_tokens", nullable = false)
    private long inputTokens;

    @Column(name = "cached_input_tokens", nullable = false)
    private long cachedInputTokens;

    @Column(name = "output_tokens", nullable = false)
    private long outputTokens;

    @Column(name = "reasoning_tokens", nullable = false)
    private long reasoningTokens;

    @Column(name = "total_tokens", nullable = false)
    private long totalTokens;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "raw_usage", columnDefinition = "jsonb")
    private Map<String, Object> rawUsage;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
