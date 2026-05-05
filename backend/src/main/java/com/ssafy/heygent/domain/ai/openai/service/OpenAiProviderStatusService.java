package com.ssafy.heygent.domain.ai.openai.service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiModelListResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiProviderStatusItemResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiProviderStatusResponse;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiProviderStatusService {

    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiRuntimePolicyService runtimePolicyService;

    @Transactional(readOnly = true)
    public OpenAiModelListResponse getModels() {
        return OpenAiModelListResponse.builder()
            .defaultModel(runtimePolicyService.defaultModel())
            .models(runtimePolicyService.allowedModels())
            .build();
    }

    @Transactional(readOnly = true)
    public OpenAiProviderStatusResponse getProviders(Long userId) {
        List<OpenAiProviderStatusItemResponse> providers = new ArrayList<>();
        providers.add(userApiKeyStatus(userId));
        providers.add(oauthStatus(userId));
        if (runtimePolicyService.isDevFallbackProfile()) {
            providers.add(devFallbackStatus());
        }

        return OpenAiProviderStatusResponse.builder()
            .providers(providers)
            .build();
    }

    private OpenAiProviderStatusItemResponse userApiKeyStatus(Long userId) {
        boolean connected = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .isPresent();

        return OpenAiProviderStatusItemResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .authType(OpenAiProviderName.OPENAI_USER_API_KEY.getAuthType())
            .connected(connected)
            .available(connected)
            .expiresAt(null)
            .status(connected ? "connected" : "not_connected")
            .build();
    }

    private OpenAiProviderStatusItemResponse oauthStatus(Long userId) {
        return openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_OAUTH.getValue())
            .map(this::connectedOauthStatus)
            .orElseGet(() -> OpenAiProviderStatusItemResponse.builder()
                .providerName(OpenAiProviderName.OPENAI_OAUTH.getValue())
                .authType(OpenAiProviderName.OPENAI_OAUTH.getAuthType())
                .connected(false)
                .available(false)
                .expiresAt(null)
                .status("not_connected")
                .build());
    }

    private OpenAiProviderStatusItemResponse connectedOauthStatus(OpenAiProviderConnection connection) {
        boolean available = !connection.isExpired(LocalDateTime.now())
            || StringUtils.hasText(connection.getEncryptedRefreshToken());
        return OpenAiProviderStatusItemResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_OAUTH.getValue())
            .authType(OpenAiProviderName.OPENAI_OAUTH.getAuthType())
            .connected(true)
            .available(available)
            .expiresAt(connection.getExpiresAt())
            .status(available ? "connected" : "expired")
            .build();
    }

    private OpenAiProviderStatusItemResponse devFallbackStatus() {
        boolean available = runtimePolicyService.isDevFallbackAvailable();
        return OpenAiProviderStatusItemResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_DEV_FALLBACK.getValue())
            .authType(OpenAiProviderName.OPENAI_DEV_FALLBACK.getAuthType())
            .connected(available)
            .available(available)
            .expiresAt(null)
            .status(available ? "available" : "disabled")
            .build();
    }
}
