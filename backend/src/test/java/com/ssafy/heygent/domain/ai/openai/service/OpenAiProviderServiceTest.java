package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.ai.openai.client.OpenAiResponsesClient;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class OpenAiProviderServiceTest {

    @Mock
    private OpenAiResponsesClient responsesClient;

    @Mock
    private OpenAiOAuthService openAiOAuthService;

    private OpenAiProperties properties;
    private OpenAiProviderService openAiProviderService;

    @BeforeEach
    void setUp() {
        properties = new OpenAiProperties();
        properties.setApiKey("test-api-key");
        properties.setDefaultModel("gpt-5.4");
        properties.setAllowedModels(List.of("gpt-5.4", "gpt-5.4-mini"));
        openAiProviderService = new OpenAiProviderService(properties, responsesClient, openAiOAuthService);
    }

    @Test
    void createResponseUsesApiKeyProviderAndDefaultModel() {
        OpenAiResponsesCommand command = command(null, null);
        OpenAiResponsesResult expected = result("openai_api", "gpt-5.4");

        when(responsesClient.callWithApiKey(
            any(OpenAiResponsesCommand.class),
            eq("gpt-5.4"),
            eq("test-api-key"),
            eq(OpenAiProviderName.OPENAI_API)
        )).thenReturn(expected);

        OpenAiResponsesResult response = openAiProviderService.createResponse(command);

        assertThat(response).isEqualTo(expected);
        assertThat(response.providerName()).isEqualTo("openai_api");
        assertThat(response.model()).isEqualTo("gpt-5.4");
    }

    @Test
    void createResponseUsesRequestedAllowedModel() {
        OpenAiResponsesCommand command = command("openai_api", "gpt-5.4-mini");
        OpenAiResponsesResult expected = result("openai_api", "gpt-5.4-mini");

        when(responsesClient.callWithApiKey(
            any(OpenAiResponsesCommand.class),
            eq("gpt-5.4-mini"),
            eq("test-api-key"),
            eq(OpenAiProviderName.OPENAI_API)
        )).thenReturn(expected);

        OpenAiResponsesResult response = openAiProviderService.createResponse(command);

        assertThat(response.model()).isEqualTo("gpt-5.4-mini");
    }

    @Test
    void createResponseFailsWhenModelIsNotAllowed() {
        OpenAiResponsesCommand command = command("openai_api", "not-allowed-model");

        assertThatThrownBy(() -> openAiProviderService.createResponse(command))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.OPENAI_MODEL_NOT_ALLOWED);
    }

    @Test
    void createResponseFailsWhenApiKeyIsMissing() {
        properties.setApiKey("");
        OpenAiResponsesCommand command = command("openai_api", "gpt-5.4");

        assertThatThrownBy(() -> openAiProviderService.createResponse(command))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
    }

    @Test
    void createResponseFailsWhenProviderIsUnsupported() {
        OpenAiResponsesCommand command = command("unknown_provider", "gpt-5.4");

        assertThatThrownBy(() -> openAiProviderService.createResponse(command))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED);
    }

    @Test
    void createResponseUsesOAuthProviderToken() {
        OpenAiResponsesCommand command = command("openai_oauth", "gpt-5.4");
        OpenAiResponsesResult expected = result("openai_oauth", "gpt-5.4");

        when(openAiOAuthService.resolveAccessToken(1L)).thenReturn("oauth-access-token");
        when(responsesClient.callWithBearerToken(
            any(OpenAiResponsesCommand.class),
            eq("gpt-5.4"),
            eq("oauth-access-token"),
            eq(OpenAiProviderName.OPENAI_OAUTH)
        )).thenReturn(expected);

        OpenAiResponsesResult response = openAiProviderService.createResponse(command);

        assertThat(response).isEqualTo(expected);
        assertThat(response.providerName()).isEqualTo("openai_oauth");
    }

    @Test
    void createResponseFailsWhenOauthProviderHasNoUserId() {
        OpenAiResponsesCommand command = new OpenAiResponsesCommand(
            null,
            "task-1",
            "step-1",
            "openai_oauth",
            "gpt-5.4",
            List.of(Map.of("role", "user", "content", "hello")),
            List.of(),
            null,
            Map.of("sessionKey", "workspace-a")
        );

        assertThatThrownBy(() -> openAiProviderService.createResponse(command))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.INVALID_INPUT_VALUE);
    }

    @Test
    void createResponseFailsWhenInputIsEmpty() {
        OpenAiResponsesCommand command = new OpenAiResponsesCommand(
            1L,
            "task-1",
            "step-1",
            "openai_api",
            "gpt-5.4",
            List.of(),
            List.of(),
            null,
            Map.of()
        );

        assertThatThrownBy(() -> openAiProviderService.createResponse(command))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.INVALID_INPUT_VALUE);
    }

    private OpenAiResponsesCommand command(String providerName, String model) {
        return new OpenAiResponsesCommand(
            1L,
            "task-1",
            "step-1",
            providerName,
            model,
            List.of(Map.of("role", "user", "content", "hello")),
            List.of(),
            null,
            Map.of("sessionKey", "workspace-a")
        );
    }

    private OpenAiResponsesResult result(String providerName, String model) {
        return new OpenAiResponsesResult(
            providerName,
            "api_key",
            model,
            "resp-1",
            "hello",
            List.of(),
            "stop",
            OpenAiUsage.empty(),
            Map.of("id", "resp-1")
        );
    }
}
