package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.ai.dto.request.AiCommandUsageRecordRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageListResponse;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageRecordResponse;
import com.ssafy.heygent.domain.ai.openai.entity.AiCommandUsageRecord;
import com.ssafy.heygent.domain.ai.openai.repository.AiCommandUsageRecordRepository;
import com.ssafy.heygent.global.exception.CustomException;

@ExtendWith(MockitoExtension.class)
class AiCommandUsageServiceTest {

    @Mock
    private AiCommandUsageRecordRepository aiCommandUsageRecordRepository;

    private AiCommandUsageService aiCommandUsageService;

    @BeforeEach
    void setUp() {
        aiCommandUsageService = new AiCommandUsageService(aiCommandUsageRecordRepository);
    }

    @Test
    void recordSavesCommandUsage() throws Exception {
        AiCommandUsageRecordRequest request = request("openai_api_key", "gpt-5.4");
        when(aiCommandUsageRecordRepository.findByUserIdAndRequestId(1L, "req-1"))
            .thenReturn(Optional.empty());
        when(aiCommandUsageRecordRepository.save(any()))
            .thenAnswer(invocation -> invocation.getArgument(0));

        AiCommandUsageRecordResponse response = aiCommandUsageService.record(request);

        ArgumentCaptor<AiCommandUsageRecord> captor = ArgumentCaptor.forClass(AiCommandUsageRecord.class);
        verify(aiCommandUsageRecordRepository).save(captor.capture());
        assertThat(captor.getValue().getProviderName()).isEqualTo("openai_api_key");
        assertThat(captor.getValue().getTaskRunId()).isEqualTo("task-1");
        assertThat(captor.getValue().getInputTokens()).isEqualTo(1200);
        assertThat(captor.getValue().getOutputTokens()).isEqualTo(300);
        assertThat(captor.getValue().getTotalTokens()).isEqualTo(1500);
        assertThat(captor.getValue().getEstimatedCostUsd()).isEqualByComparingTo("0.0042");
        assertThat(response.getCurrency()).isEqualTo("USD");
    }

    @Test
    void recordReturnsExistingRecordWhenRequestIdIsDuplicated() throws Exception {
        AiCommandUsageRecord existing = AiCommandUsageRecord.builder()
            .userId(1L)
            .providerName("gemini_api_key")
            .model("gemini-2.5-pro")
            .taskRunId("task-1")
            .requestId("req-1")
            .inputTokens(10L)
            .outputTokens(5L)
            .totalTokens(15L)
            .currency("USD")
            .metadata(Map.of())
            .build();
        when(aiCommandUsageRecordRepository.findByUserIdAndRequestId(1L, "req-1"))
            .thenReturn(Optional.of(existing));

        AiCommandUsageRecordResponse response = aiCommandUsageService.record(request("gemini_api_key", "gemini-2.5-pro"));

        assertThat(response.getProviderName()).isEqualTo("gemini_api_key");
        assertThat(response.getTotalTokens()).isEqualTo(15);
    }

    @Test
    void recordRejectsUnsupportedProvider() throws Exception {
        AiCommandUsageRecordRequest request = request("openai_codex_oauth", "gpt-5.3-codex");

        assertThatThrownBy(() -> aiCommandUsageService.record(request))
            .isInstanceOf(CustomException.class);
    }

    @Test
    void getMyUsagesReturnsSummary() {
        when(aiCommandUsageRecordRepository.findUsageRecords(
            eq(1L),
            eq("task-1"),
            eq(null),
            eq(null),
            eq(null),
            any()
        )).thenReturn(List.of(
            usage("openai_api_key", 100L, 20L, 120L, "0.0010"),
            usage("claude_api_key", 200L, 30L, 230L, "0.0020")
        ));

        AiCommandUsageListResponse response = aiCommandUsageService.getMyUsages(
            1L,
            null,
            null,
            "task-1",
            null,
            50
        );

        assertThat(response.getRecords()).hasSize(2);
        assertThat(response.getSummary().getInputTokens()).isEqualTo(300);
        assertThat(response.getSummary().getOutputTokens()).isEqualTo(50);
        assertThat(response.getSummary().getTotalTokens()).isEqualTo(350);
        assertThat(response.getSummary().getEstimatedCostUsd()).isEqualByComparingTo("0.0030");
        assertThat(response.getSummary().getRecordCount()).isEqualTo(2);
    }

    private AiCommandUsageRecord usage(
        String providerName,
        Long inputTokens,
        Long outputTokens,
        Long totalTokens,
        String estimatedCostUsd
    ) {
        return AiCommandUsageRecord.builder()
            .userId(1L)
            .providerName(providerName)
            .model("model")
            .taskRunId("task-1")
            .inputTokens(inputTokens)
            .outputTokens(outputTokens)
            .totalTokens(totalTokens)
            .estimatedCostUsd(new BigDecimal(estimatedCostUsd))
            .currency("USD")
            .metadata(Map.of())
            .build();
    }

    private AiCommandUsageRecordRequest request(String providerName, String model) throws Exception {
        AiCommandUsageRecordRequest request = new AiCommandUsageRecordRequest();
        set(request, "userId", 1L);
        set(request, "providerName", providerName);
        set(request, "model", model);
        set(request, "taskRunId", "task-1");
        set(request, "stepRunId", "step-1");
        set(request, "sessionId", "session-1");
        set(request, "requestId", "req-1");
        set(request, "inputTokens", 1200L);
        set(request, "outputTokens", 300L);
        set(request, "totalTokens", 1500L);
        set(request, "estimatedCostUsd", new BigDecimal("0.0042"));
        set(request, "metadata", Map.of("finishReason", "stop"));
        return request;
    }

    private void set(Object target, String name, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }
}
