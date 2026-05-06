package com.ssafy.heygent.domain.ai.openai.service;

import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiApiKeyConnectionResponse;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;
import com.ssafy.heygent.domain.ai.openai.security.OpenAiCredentialCipher;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiApiKeyService {

    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiCredentialCipher credentialCipher;

    @Transactional
    public OpenAiApiKeyConnectionResponse upsert(Long userId, String apiKey) {
        if (!StringUtils.hasText(apiKey)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        OpenAiProviderConnection connection = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .orElseGet(() -> OpenAiProviderConnection.builder()
                .userId(userId)
                .providerName(OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
                .build());

        connection.updateToken(
            "ApiKey",
            credentialCipher.encrypt(apiKey.trim()),
            null,
            "",
            null,
            Map.of("source", "user")
        );

        OpenAiProviderConnection saved = openAiProviderConnectionRepository.save(connection);
        return OpenAiApiKeyConnectionResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .connected(true)
            .status("connected")
            .updatedAt(saved.getUpdatedAt())
            .build();
    }

    @Transactional
    public OpenAiApiKeyConnectionResponse delete(Long userId) {
        openAiProviderConnectionRepository.deleteByUserIdAndProviderName(
            userId,
            OpenAiProviderName.OPENAI_USER_API_KEY.getValue()
        );

        return OpenAiApiKeyConnectionResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .connected(false)
            .status("disconnected")
            .updatedAt(null)
            .build();
    }

    @Transactional(readOnly = true)
    public String resolveApiKey(Long userId) {
        OpenAiProviderConnection connection = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_USER_API_KEY.getValue())
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONNECTED));
        return credentialCipher.decrypt(connection.getEncryptedAccessToken());
    }
}
