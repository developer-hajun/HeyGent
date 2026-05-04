package com.ssafy.heygent.domain.ai.openai.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

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

    public OpenAiResponsesResult createResponse(OpenAiResponsesCommand command) {
        validateInput(command);

        OpenAiProviderName providerName = OpenAiProviderName.from(command.providerName());
        String model = resolveModel(command.model());

        if (providerName == OpenAiProviderName.OPENAI_API) {
            if (!properties.hasApiKey()) {
                throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
            }
            return responsesClient.callWithApiKey(command, model, properties.getApiKey(), providerName);
        }

        if (command.userId() == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        String accessToken = openAiOAuthService.resolveAccessToken(command.userId());
        return responsesClient.callWithBearerToken(command, model, accessToken, providerName);
    }

    public String resolveModel(String requestedModel) {
        String model = StringUtils.hasText(requestedModel)
            ? requestedModel.trim()
            : properties.getDefaultModel();

        List<String> allowedModels = properties.normalizedAllowedModels();
        if (!allowedModels.isEmpty() && !allowedModels.contains(model)) {
            throw new CustomException(ErrorCode.OPENAI_MODEL_NOT_ALLOWED);
        }
        return model;
    }

    private void validateInput(OpenAiResponsesCommand command) {
        if (command == null || command.input() == null || command.input().isEmpty()) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }
}
