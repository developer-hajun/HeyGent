package com.ssafy.heygent.domain.ai.openai.service;

import org.springframework.stereotype.Service;

import com.ssafy.heygent.domain.ai.openai.client.OpenAiResponsesClient;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiProviderService {

    private final OpenAiProperties properties;
    private final OpenAiResponsesClient responsesClient;
    private final OpenAiOAuthService openAiOAuthService;
    private final OpenAiApiKeyService openAiApiKeyService;
    private final OpenAiRuntimePolicyService runtimePolicyService;

    public OpenAiResponsesResult createResponse(OpenAiResponsesCommand command) {
        validateInput(command);

        OpenAiProviderName providerName = OpenAiProviderName.from(command.providerName());
        String model = resolveModel(command.model());

        if (command.userId() == null && providerName != OpenAiProviderName.OPENAI_DEV_FALLBACK) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        if (providerName == OpenAiProviderName.OPENAI_USER_API_KEY) {
            String apiKey = openAiApiKeyService.resolveApiKey(command.userId());
            return responsesClient.callWithApiKey(command, model, apiKey, providerName);
        }

        if (providerName == OpenAiProviderName.OPENAI_OAUTH) {
            String accessToken = openAiOAuthService.resolveAccessToken(command.userId());
            return responsesClient.callWithBearerToken(command, model, accessToken, providerName);
        }

        runtimePolicyService.validateDevFallbackAvailable();
        return responsesClient.callWithApiKey(command, model, properties.getApiKey(), providerName);
    }

    public String resolveModel(String requestedModel) {
        return runtimePolicyService.resolveAllowedModelOrDefault(requestedModel);
    }

    private void validateInput(OpenAiResponsesCommand command) {
        if (command == null || command.input() == null || command.input().isEmpty()) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }
}
