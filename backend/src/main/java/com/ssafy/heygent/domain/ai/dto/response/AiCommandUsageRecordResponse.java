package com.ssafy.heygent.domain.ai.dto.response;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

import com.ssafy.heygent.domain.ai.openai.entity.AiCommandUsageRecord;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AiCommandUsageRecordResponse {

    private Long id;
    private Long userId;
    private String providerName;
    private String model;
    private String taskRunId;
    private String stepRunId;
    private String sessionId;
    private String requestId;
    private Long inputTokens;
    private Long outputTokens;
    private Long totalTokens;
    private Long cachedInputTokens;
    private Long reasoningTokens;
    private BigDecimal estimatedCostUsd;
    private String currency;
    private Map<String, Object> metadata;
    private LocalDateTime createdAt;

    public static AiCommandUsageRecordResponse from(AiCommandUsageRecord record) {
        return AiCommandUsageRecordResponse.builder()
            .id(record.getId())
            .userId(record.getUserId())
            .providerName(record.getProviderName())
            .model(record.getModel())
            .taskRunId(record.getTaskRunId())
            .stepRunId(record.getStepRunId())
            .sessionId(record.getSessionId())
            .requestId(record.getRequestId())
            .inputTokens(record.getInputTokens())
            .outputTokens(record.getOutputTokens())
            .totalTokens(record.getTotalTokens())
            .cachedInputTokens(record.getCachedInputTokens())
            .reasoningTokens(record.getReasoningTokens())
            .estimatedCostUsd(record.getEstimatedCostUsd())
            .currency(record.getCurrency())
            .metadata(record.getMetadata())
            .createdAt(record.getCreatedAt())
            .build();
    }
}
