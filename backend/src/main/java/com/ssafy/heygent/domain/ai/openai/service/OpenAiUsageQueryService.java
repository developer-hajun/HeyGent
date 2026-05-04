package com.ssafy.heygent.domain.ai.openai.service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageDailyResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageSummaryResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageTotalResponse;
import com.ssafy.heygent.domain.ai.openai.entity.AiTokenUsageLog;
import com.ssafy.heygent.domain.ai.openai.repository.AiTokenUsageLogRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OpenAiUsageQueryService {

    private final AiTokenUsageLogRepository aiTokenUsageLogRepository;

    public OpenAiUsageSummaryResponse getMyUsage(Long userId, LocalDate from, LocalDate to) {
        LocalDateTime fromDateTime = from == null ? null : from.atStartOfDay();
        LocalDateTime toDateTime = to == null ? null : to.plusDays(1).atStartOfDay();

        List<AiTokenUsageLog> logs = aiTokenUsageLogRepository.findUserLogs(userId, fromDateTime, toDateTime);
        UsageAccumulator total = new UsageAccumulator();
        Map<LocalDate, UsageAccumulator> daily = new LinkedHashMap<>();

        for (AiTokenUsageLog log : logs) {
            total.add(log);
            LocalDate date = log.getCreatedAt().toLocalDate();
            daily.computeIfAbsent(date, ignored -> new UsageAccumulator()).add(log);
        }

        List<OpenAiUsageDailyResponse> items = daily.entrySet().stream()
            .sorted(Map.Entry.comparingByKey(Comparator.naturalOrder()))
            .map(entry -> entry.getValue().toDailyResponse(entry.getKey()))
            .toList();

        return OpenAiUsageSummaryResponse.builder()
            .from(from)
            .to(to)
            .total(total.toTotalResponse())
            .items(items)
            .build();
    }

    private static class UsageAccumulator {

        private long requestCount;
        private long inputTokens;
        private long cachedInputTokens;
        private long outputTokens;
        private long reasoningTokens;
        private long totalTokens;

        void add(AiTokenUsageLog log) {
            requestCount++;
            inputTokens += log.getInputTokens();
            cachedInputTokens += log.getCachedInputTokens();
            outputTokens += log.getOutputTokens();
            reasoningTokens += log.getReasoningTokens();
            totalTokens += log.getTotalTokens();
        }

        OpenAiUsageTotalResponse toTotalResponse() {
            return OpenAiUsageTotalResponse.builder()
                .requestCount(requestCount)
                .inputTokens(inputTokens)
                .cachedInputTokens(cachedInputTokens)
                .outputTokens(outputTokens)
                .reasoningTokens(reasoningTokens)
                .totalTokens(totalTokens)
                .build();
        }

        OpenAiUsageDailyResponse toDailyResponse(LocalDate date) {
            return OpenAiUsageDailyResponse.builder()
                .date(date)
                .requestCount(requestCount)
                .inputTokens(inputTokens)
                .cachedInputTokens(cachedInputTokens)
                .outputTokens(outputTokens)
                .reasoningTokens(reasoningTokens)
                .totalTokens(totalTokens)
                .build();
        }
    }
}
