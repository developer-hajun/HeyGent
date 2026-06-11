package com.ssafy.heygent.domain.ai.openai.service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.dto.response.AiProviderModelItemResponse;
import com.ssafy.heygent.domain.ai.dto.response.AiProviderModelListResponse;
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
    public AiProviderModelListResponse getProviderModels() {
        List<AiProviderModelItemResponse> providers = modelProviders().stream()
            .map(providerName -> AiProviderModelItemResponse.builder()
                .providerName(providerName.getValue())
                .providerType(providerName.getProviderType())
                .authType(providerName.getAuthType())
                .displayName(providerName.getDisplayName())
                .description(providerName.getDescription())
                .connectType(providerName.getConnectType())
                .defaultModel(runtimePolicyService.defaultModel(providerName))
                .models(runtimePolicyService.allowedModels(providerName))
                .build())
            .toList();

        return AiProviderModelListResponse.builder()
            .defaultModel(runtimePolicyService.defaultModel())
            .providers(providers)
            .build();
    }

    @Transactional(readOnly = true)
    public OpenAiProviderStatusResponse getProviders(Long userId) {
        List<OpenAiProviderStatusItemResponse> providers = new ArrayList<>();
        for (OpenAiProviderName providerName : userManagedProviders()) {
            providers.add(userApiKeyStatus(userId, providerName));
        }
        if (runtimePolicyService.isDevFallbackProfile()) {
            providers.add(devFallbackStatus());
        }

        return OpenAiProviderStatusResponse.builder()
            .providers(providers)
            .build();
    }

    private List<OpenAiProviderName> userManagedProviders() {
        return List.of(
            OpenAiProviderName.OPENAI_API_KEY,
            OpenAiProviderName.GEMINI_API_KEY,
            OpenAiProviderName.CLAUDE_API_KEY
        );
    }

    private List<OpenAiProviderName> modelProviders() {
        return List.of(
            OpenAiProviderName.OPENAI_API_KEY,
            OpenAiProviderName.GEMINI_API_KEY,
            OpenAiProviderName.CLAUDE_API_KEY
        );
    }

    private OpenAiProviderStatusItemResponse userApiKeyStatus(Long userId, OpenAiProviderName providerName) {
        boolean connected = providerName.lookupValues().stream()
            .anyMatch(lookupValue -> openAiProviderConnectionRepository
                .findByUserIdAndProviderName(userId, lookupValue)
                .isPresent());

        return OpenAiProviderStatusItemResponse.builder()
            .providerName(providerName.getValue())
            .providerType(providerName.getProviderType())
            .authType(providerName.getAuthType())
            .displayName(providerName.getDisplayName())
            .description(providerName.getDescription())
            .connectType(providerName.getConnectType())
            .defaultModel(runtimePolicyService.defaultModel(providerName))
            .models(runtimePolicyService.allowedModels(providerName))
            .connected(connected)
            .available(connected)
            .expiresAt(null)
            .status(connected ? "connected" : "not_connected")
            .build();
    }

    private OpenAiProviderStatusItemResponse codexOAuthStatus(Long userId) {
        return openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .map(this::connectedCodexOAuthStatus)
            .orElseGet(() -> OpenAiProviderStatusItemResponse.builder()
                .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
                .providerType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getProviderType())
                .authType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getAuthType())
                .displayName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getDisplayName())
                .description(OpenAiProviderName.OPENAI_CODEX_OAUTH.getDescription())
                .connectType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getConnectType())
                .defaultModel(runtimePolicyService.defaultModel(OpenAiProviderName.OPENAI_CODEX_OAUTH))
                .models(runtimePolicyService.allowedModels(OpenAiProviderName.OPENAI_CODEX_OAUTH))
                .connected(false)
                .available(false)
                .expiresAt(null)
                .status("not_connected")
                .build());
    }

    private OpenAiProviderStatusItemResponse connectedCodexOAuthStatus(OpenAiProviderConnection connection) {
        boolean available = !connection.isExpired(LocalDateTime.now())
            || StringUtils.hasText(connection.getEncryptedRefreshToken());
        return OpenAiProviderStatusItemResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .providerType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getProviderType())
            .authType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getAuthType())
            .displayName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getDisplayName())
            .description(OpenAiProviderName.OPENAI_CODEX_OAUTH.getDescription())
            .connectType(OpenAiProviderName.OPENAI_CODEX_OAUTH.getConnectType())
            .defaultModel(runtimePolicyService.defaultModel(OpenAiProviderName.OPENAI_CODEX_OAUTH))
            .models(runtimePolicyService.allowedModels(OpenAiProviderName.OPENAI_CODEX_OAUTH))
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
            .providerType(OpenAiProviderName.OPENAI_DEV_FALLBACK.getProviderType())
            .authType(OpenAiProviderName.OPENAI_DEV_FALLBACK.getAuthType())
            .displayName(OpenAiProviderName.OPENAI_DEV_FALLBACK.getDisplayName())
            .description(OpenAiProviderName.OPENAI_DEV_FALLBACK.getDescription())
            .connectType(OpenAiProviderName.OPENAI_DEV_FALLBACK.getConnectType())
            .defaultModel(runtimePolicyService.defaultModel(OpenAiProviderName.OPENAI_DEV_FALLBACK))
            .models(runtimePolicyService.allowedModels(OpenAiProviderName.OPENAI_DEV_FALLBACK))
            .connected(available)
            .available(available)
            .expiresAt(null)
            .status(available ? "available" : "disabled")
            .build();
    }
}
