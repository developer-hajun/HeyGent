package com.ssafy.heygent.domain.ai.openai.service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.dto.request.AiCommandUsageRecordRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageListResponse;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageRecordResponse;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageSummaryResponse;
import com.ssafy.heygent.domain.ai.openai.entity.AiCommandUsageRecord;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.AiCommandUsageRecordRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AiCommandUsageService {

    private static final String DEFAULT_CURRENCY = "USD";
    private static final int DEFAULT_LIMIT = 100;
    private static final int MAX_LIMIT = 500;

    private final AiCommandUsageRecordRepository aiCommandUsageRecordRepository;

    @Transactional
    public AiCommandUsageRecordResponse record(AiCommandUsageRecordRequest request) {
        OpenAiProviderName providerName = OpenAiProviderName.from(request.getProviderName());
        if (!providerName.isUserManagedApiKeyProvider()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED);
        }

        String requestId = trimToNull(request.getRequestId());
        if (StringUtils.hasText(requestId)) {
            return aiCommandUsageRecordRepository.findByUserIdAndRequestId(request.getUserId(), requestId)
                .map(AiCommandUsageRecordResponse::from)
                .orElseGet(() -> save(request, providerName, requestId));
        }
        return save(request, providerName, null);
    }

    @Transactional(readOnly = true)
    public AiCommandUsageListResponse getMyUsages(
        Long userId,
        LocalDate from,
        LocalDate to,
        String taskRunId,
        String sessionId,
        Integer limit
    ) {
        List<AiCommandUsageRecord> records = aiCommandUsageRecordRepository.findUsageRecords(
            userId,
            trimToNull(taskRunId),
            trimToNull(sessionId),
            startOfDay(from),
            endExclusive(to),
            PageRequest.of(0, normalizeLimit(limit))
        );

        return AiCommandUsageListResponse.builder()
            .summary(summary(records))
            .records(records.stream()
                .map(AiCommandUsageRecordResponse::from)
                .toList())
            .build();
    }

    private AiCommandUsageRecordResponse save(
        AiCommandUsageRecordRequest request,
        OpenAiProviderName providerName,
        String requestId
    ) {
        long inputTokens = valueOrZero(request.getInputTokens());
        long outputTokens = valueOrZero(request.getOutputTokens());
        long totalTokens = request.getTotalTokens() == null
            ? inputTokens + outputTokens
            : request.getTotalTokens();

        AiCommandUsageRecord record = AiCommandUsageRecord.builder()
            .userId(request.getUserId())
            .providerName(providerName.getValue())
            .model(request.getModel().trim())
            .taskRunId(request.getTaskRunId().trim())
            .stepRunId(trimToNull(request.getStepRunId()))
            .sessionId(trimToNull(request.getSessionId()))
            .requestId(requestId)
            .inputTokens(inputTokens)
            .outputTokens(outputTokens)
            .totalTokens(totalTokens)
            .cachedInputTokens(request.getCachedInputTokens())
            .reasoningTokens(request.getReasoningTokens())
            .estimatedCostUsd(request.getEstimatedCostUsd())
            .currency(DEFAULT_CURRENCY)
            .metadata(normalizeMetadata(request.getMetadata()))
            .build();

        return AiCommandUsageRecordResponse.from(aiCommandUsageRecordRepository.save(record));
    }

    private AiCommandUsageSummaryResponse summary(List<AiCommandUsageRecord> records) {
        long inputTokens = 0;
        long outputTokens = 0;
        long totalTokens = 0;
        long cachedInputTokens = 0;
        long reasoningTokens = 0;
        BigDecimal estimatedCostUsd = BigDecimal.ZERO;

        for (AiCommandUsageRecord record : records) {
            inputTokens += valueOrZero(record.getInputTokens());
            outputTokens += valueOrZero(record.getOutputTokens());
            totalTokens += valueOrZero(record.getTotalTokens());
            cachedInputTokens += valueOrZero(record.getCachedInputTokens());
            reasoningTokens += valueOrZero(record.getReasoningTokens());
            if (record.getEstimatedCostUsd() != null) {
                estimatedCostUsd = estimatedCostUsd.add(record.getEstimatedCostUsd());
            }
        }

        return AiCommandUsageSummaryResponse.builder()
            .inputTokens(inputTokens)
            .outputTokens(outputTokens)
            .totalTokens(totalTokens)
            .cachedInputTokens(cachedInputTokens)
            .reasoningTokens(reasoningTokens)
            .estimatedCostUsd(estimatedCostUsd)
            .currency(DEFAULT_CURRENCY)
            .recordCount(records.size())
            .build();
    }

    private int normalizeLimit(Integer limit) {
        if (limit == null) {
            return DEFAULT_LIMIT;
        }
        if (limit < 1) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return Math.min(limit, MAX_LIMIT);
    }

    private LocalDateTime startOfDay(LocalDate date) {
        return date == null ? null : date.atStartOfDay();
    }

    private LocalDateTime endExclusive(LocalDate date) {
        return date == null ? null : date.plusDays(1).atStartOfDay();
    }

    private Map<String, Object> normalizeMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        return metadata;
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }

    private long valueOrZero(Long value) {
        return value == null ? 0L : value;
    }
}
