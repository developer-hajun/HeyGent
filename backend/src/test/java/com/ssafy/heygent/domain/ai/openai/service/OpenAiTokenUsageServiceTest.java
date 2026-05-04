package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;
import com.ssafy.heygent.domain.ai.openai.entity.AiTokenUsageLog;
import com.ssafy.heygent.domain.ai.openai.repository.AiTokenUsageLogRepository;

@ExtendWith(MockitoExtension.class)
class OpenAiTokenUsageServiceTest {

    @Mock
    private AiTokenUsageLogRepository aiTokenUsageLogRepository;

    private OpenAiTokenUsageService openAiTokenUsageService;

    @BeforeEach
    void setUp() {
        openAiTokenUsageService = new OpenAiTokenUsageService(aiTokenUsageLogRepository);
    }

    @Test
    void recordSavesOpenAiUsageLog() {
        OpenAiResponsesCommand command = new OpenAiResponsesCommand(
            1L,
            "task-1",
            "step-1",
            "openai_api",
            "gpt-5.4",
            List.of(Map.of("role", "user", "content", "hello")),
            List.of(),
            null,
            Map.of("sessionKey", "workspace-a")
        );
        OpenAiResponsesResult result = new OpenAiResponsesResult(
            "openai_api",
            "api_key",
            "gpt-5.4",
            "resp-1",
            "hello",
            List.of(),
            "stop",
            new OpenAiUsage(100, 20, 40, 10, 140),
            Map.of("usage", Map.of("input_tokens", 100, "total_tokens", 140))
        );
        ArgumentCaptor<AiTokenUsageLog> captor = ArgumentCaptor.forClass(AiTokenUsageLog.class);

        when(aiTokenUsageLogRepository.save(any(AiTokenUsageLog.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        openAiTokenUsageService.record(command, result);

        verify(aiTokenUsageLogRepository).save(captor.capture());
        AiTokenUsageLog usageLog = captor.getValue();
        assertThat(usageLog.getUserId()).isEqualTo(1L);
        assertThat(usageLog.getTaskRunId()).isEqualTo("task-1");
        assertThat(usageLog.getStepRunId()).isEqualTo("step-1");
        assertThat(usageLog.getProviderName()).isEqualTo("openai_api");
        assertThat(usageLog.getAuthType()).isEqualTo("api_key");
        assertThat(usageLog.getModel()).isEqualTo("gpt-5.4");
        assertThat(usageLog.getResponseId()).isEqualTo("resp-1");
        assertThat(usageLog.getInputTokens()).isEqualTo(100);
        assertThat(usageLog.getCachedInputTokens()).isEqualTo(20);
        assertThat(usageLog.getOutputTokens()).isEqualTo(40);
        assertThat(usageLog.getReasoningTokens()).isEqualTo(10);
        assertThat(usageLog.getTotalTokens()).isEqualTo(140);
        assertThat(usageLog.getRawUsage()).containsEntry("input_tokens", 100);
        assertThat(usageLog.getMetadata()).containsEntry("sessionKey", "workspace-a");
    }
}
