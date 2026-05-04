package com.ssafy.heygent.domain.ai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiResponsesRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiResponsesResponse;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiProviderService;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiTokenUsageService;

@ExtendWith(MockitoExtension.class)
class AiInternalOpenAiServiceTest {

    @Mock
    private OpenAiProviderService openAiProviderService;

    @Mock
    private OpenAiTokenUsageService openAiTokenUsageService;

    private AiInternalOpenAiService aiInternalOpenAiService;

    @BeforeEach
    void setUp() {
        aiInternalOpenAiService = new AiInternalOpenAiService(openAiProviderService, openAiTokenUsageService);
    }

    @Test
    void createResponseCallsOpenAiAndRecordsUsage() {
        OpenAiResponsesRequest request = TestOpenAiResponsesRequestFactory.create(
            1L,
            "task-1",
            "step-1",
            "openai_api",
            "gpt-5.4"
        );
        OpenAiResponsesResult result = new OpenAiResponsesResult(
            "openai_api",
            "api_key",
            "gpt-5.4",
            "resp-1",
            "hello",
            List.of(),
            "stop",
            new OpenAiUsage(10, 0, 5, 0, 15),
            Map.of()
        );

        when(openAiProviderService.createResponse(org.mockito.ArgumentMatchers.any(OpenAiResponsesCommand.class)))
            .thenReturn(result);

        OpenAiResponsesResponse response = aiInternalOpenAiService.createResponse(request);

        assertThat(response.getProviderName()).isEqualTo("openai_api");
        assertThat(response.getOutputText()).isEqualTo("hello");
        assertThat(response.getUsage().getTotalTokens()).isEqualTo(15);
        verify(openAiProviderService).createResponse(org.mockito.ArgumentMatchers.any(OpenAiResponsesCommand.class));
        verify(openAiTokenUsageService).record(
            org.mockito.ArgumentMatchers.any(OpenAiResponsesCommand.class),
            org.mockito.ArgumentMatchers.eq(result)
        );
    }
}
