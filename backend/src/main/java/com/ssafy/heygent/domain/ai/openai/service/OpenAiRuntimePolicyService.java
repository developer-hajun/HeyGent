package com.ssafy.heygent.domain.ai.openai.service;

import java.util.List;

import org.springframework.core.env.Environment;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiRuntimePolicyService {

    private static final List<String> DEV_FALLBACK_PROFILES = List.of("dev", "local");

    private final OpenAiProperties properties;
    private final Environment environment;

    public String requireAllowedModel(String requestedModel) {
        return requireAllowedModel(OpenAiProviderName.OPENAI_API_KEY, requestedModel);
    }

    public String requireAllowedModel(OpenAiProviderName providerName, String requestedModel) {
        if (!StringUtils.hasText(requestedModel)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        String model = requestedModel.trim();
        List<String> allowedModels = allowedModels(providerName);
        if (!allowedModels.isEmpty() && !allowedModels.contains(model)) {
            throw new CustomException(ErrorCode.OPENAI_MODEL_NOT_ALLOWED);
        }
        return model;
    }

    public String resolveAllowedModelOrDefault(String requestedModel) {
        String model = StringUtils.hasText(requestedModel)
            ? requestedModel.trim()
            : properties.getDefaultModel();
        return requireAllowedModel(model);
    }

    public List<String> allowedModels() {
        return properties.normalizedAllowedModels();
    }

    public List<String> allowedModels(OpenAiProviderName providerName) {
        if (providerName.getProviderType().equals("openai")) {
            return properties.normalizedAllowedModels();
        }
        return providerName.getDefaultModels();
    }

    public String defaultModel() {
        return properties.getDefaultModel();
    }

    public String defaultModel(OpenAiProviderName providerName) {
        List<String> models = allowedModels(providerName);
        if (models.isEmpty()) {
            return properties.getDefaultModel();
        }
        return models.get(0);
    }

    public boolean isDevFallbackAvailable() {
        return properties.hasApiKey() && isDevProfile();
    }

    public boolean isDevFallbackProfile() {
        return isDevProfile();
    }

    public void validateDevFallbackAvailable() {
        if (!isDevFallbackAvailable()) {
            throw new CustomException(ErrorCode.OPENAI_DEV_FALLBACK_NOT_ALLOWED);
        }
    }

    private boolean isDevProfile() {
        for (String profile : DEV_FALLBACK_PROFILES) {
            if (environment.matchesProfiles(profile)) {
                return true;
            }
        }
        return false;
    }
}
