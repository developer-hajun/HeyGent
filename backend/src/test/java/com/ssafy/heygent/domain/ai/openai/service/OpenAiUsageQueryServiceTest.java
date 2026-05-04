package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageSummaryResponse;
import com.ssafy.heygent.domain.ai.openai.entity.AiTokenUsageLog;
import com.ssafy.heygent.domain.ai.openai.repository.AiTokenUsageLogRepository;

@ExtendWith(MockitoExtension.class)
class OpenAiUsageQueryServiceTest {

    @Mock
    private AiTokenUsageLogRepository aiTokenUsageLogRepository;

    private OpenAiUsageQueryService openAiUsageQueryService;

    @BeforeEach
    void setUp() {
        openAiUsageQueryService = new OpenAiUsageQueryService(aiTokenUsageLogRepository);
    }

    @Test
    void getMyUsageReturnsTotalAndDailyUsage() {
        LocalDate from = LocalDate.of(2026, 5, 1);
        LocalDate to = LocalDate.of(2026, 5, 2);
        List<AiTokenUsageLog> logs = List.of(
            usageLog(LocalDateTime.of(2026, 5, 1, 10, 0), 100, 20, 40, 10, 140),
            usageLog(LocalDateTime.of(2026, 5, 1, 11, 0), 50, 5, 30, 0, 80),
            usageLog(LocalDateTime.of(2026, 5, 2, 9, 0), 70, 0, 20, 5, 90)
        );

        when(aiTokenUsageLogRepository.findUserLogs(
            1L,
            LocalDateTime.of(2026, 5, 1, 0, 0),
            LocalDateTime.of(2026, 5, 3, 0, 0)
        )).thenReturn(logs);

        OpenAiUsageSummaryResponse response = openAiUsageQueryService.getMyUsage(1L, from, to);

        assertThat(response.getFrom()).isEqualTo(from);
        assertThat(response.getTo()).isEqualTo(to);
        assertThat(response.getTotal().getRequestCount()).isEqualTo(3);
        assertThat(response.getTotal().getInputTokens()).isEqualTo(220);
        assertThat(response.getTotal().getCachedInputTokens()).isEqualTo(25);
        assertThat(response.getTotal().getOutputTokens()).isEqualTo(90);
        assertThat(response.getTotal().getReasoningTokens()).isEqualTo(15);
        assertThat(response.getTotal().getTotalTokens()).isEqualTo(310);
        assertThat(response.getItems()).hasSize(2);
        assertThat(response.getItems().get(0).getDate()).isEqualTo(LocalDate.of(2026, 5, 1));
        assertThat(response.getItems().get(0).getRequestCount()).isEqualTo(2);
        assertThat(response.getItems().get(0).getTotalTokens()).isEqualTo(220);
        assertThat(response.getItems().get(1).getDate()).isEqualTo(LocalDate.of(2026, 5, 2));
        assertThat(response.getItems().get(1).getRequestCount()).isEqualTo(1);
        assertThat(response.getItems().get(1).getTotalTokens()).isEqualTo(90);
    }

    private AiTokenUsageLog usageLog(
        LocalDateTime createdAt,
        long inputTokens,
        long cachedInputTokens,
        long outputTokens,
        long reasoningTokens,
        long totalTokens
    ) {
        AiTokenUsageLog usageLog = AiTokenUsageLog.builder()
            .userId(1L)
            .providerName("openai_api")
            .authType("api_key")
            .model("gpt-5.4")
            .inputTokens(inputTokens)
            .cachedInputTokens(cachedInputTokens)
            .outputTokens(outputTokens)
            .reasoningTokens(reasoningTokens)
            .totalTokens(totalTokens)
            .rawUsage(Map.of())
            .metadata(Map.of())
            .build();
        ReflectionTestUtils.setField(usageLog, "createdAt", createdAt);
        return usageLog;
    }
}
