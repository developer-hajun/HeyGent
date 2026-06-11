package com.ssafy.heygent.domain.ai.openai.service;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Base64;
import java.util.List;
import java.util.Map;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCodexOAuthStatusResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;
import com.ssafy.heygent.domain.ai.openai.security.OpenAiCredentialCipher;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiCodexOAuthService {

    private static final String CODEX_SCOPE = "codex";
    private static final String TOKEN_TYPE = "Bearer";

    private final OpenAiProperties properties;
    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiCredentialCipher credentialCipher;
    private final ObjectMapper objectMapper;

    @Transactional
    public OpenAiOAuthConnectionResponse refresh(Long userId) {
        validateConfigured();

        OpenAiProviderConnection connection = getConnection(userId);
        String refreshToken = credentialCipher.decrypt(connection.getEncryptedRefreshToken());
        if (!StringUtils.hasText(refreshToken)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED);
        }

        CodexTokenPayload tokenPayload = requestToken(formForRefreshToken(refreshToken));
        OpenAiProviderConnection updated = upsertConnection(userId, tokenPayload);
        return toConnectionResponse(updated, "refreshed");
    }

    @Transactional(readOnly = true)
    public OpenAiCodexOAuthStatusResponse getStatus(Long userId) {
        return openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .map(this::toStatusResponse)
            .orElseGet(() -> OpenAiCodexOAuthStatusResponse.builder()
                .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
                .connected(false)
                .available(false)
                .status("not_connected")
                .accountId(null)
                .expiresAt(null)
                .build());
    }

    @Transactional
    public OpenAiOAuthConnectionResponse disconnect(Long userId) {
        openAiProviderConnectionRepository.deleteByUserIdAndProviderName(
            userId,
            OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue()
        );
        return OpenAiOAuthConnectionResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .connected(false)
            .status("disconnected")
            .scopes(List.of())
            .expiresAt(null)
            .build();
    }

    @Transactional
    public AccessTokenCredential resolveAccessTokenCredential(Long userId) {
        OpenAiProviderConnection connection = getConnection(userId);
        if (shouldRefresh(connection)) {
            refresh(userId);
            connection = getConnection(userId);
        }
        if (connection.isExpired(LocalDateTime.now())) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED);
        }
        return new AccessTokenCredential(
            credentialCipher.decrypt(connection.getEncryptedAccessToken()),
            connection.getExpiresAt()
        );
    }

    private boolean shouldRefresh(OpenAiProviderConnection connection) {
        if (!StringUtils.hasText(connection.getEncryptedRefreshToken()) || connection.getExpiresAt() == null) {
            return false;
        }
        return !connection.getExpiresAt()
            .isAfter(LocalDateTime.now().plusSeconds(properties.getCodexOAuth().getRefreshSkewSeconds()));
    }

    private OpenAiProviderConnection getConnection(Long userId) {
        return openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED));
    }

    private OpenAiProviderConnection upsertConnection(Long userId, CodexTokenPayload tokenPayload) {
        OpenAiProviderConnection connection = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .orElseGet(() -> OpenAiProviderConnection.builder()
                .userId(userId)
                .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
                .build());

        String refreshToken = StringUtils.hasText(tokenPayload.refreshToken())
            ? tokenPayload.refreshToken()
            : credentialCipher.decrypt(connection.getEncryptedRefreshToken());
        String accountId = StringUtils.hasText(tokenPayload.accountId())
            ? tokenPayload.accountId()
            : valueOrNull(connection.getMetadata(), "accountId");
        connection.updateToken(
            TOKEN_TYPE,
            credentialCipher.encrypt(tokenPayload.accessToken()),
            credentialCipher.encrypt(refreshToken),
            CODEX_SCOPE,
            tokenPayload.expiresAt(),
            Map.of(
                "accountId", valueOrEmpty(accountId),
                "credentialFormat", "device_oauth",
                "hasRefreshToken", StringUtils.hasText(refreshToken)
            )
        );
        return openAiProviderConnectionRepository.save(connection);
    }

    private OpenAiOAuthConnectionResponse toConnectionResponse(OpenAiProviderConnection connection, String status) {
        return OpenAiOAuthConnectionResponse.builder()
            .providerName(connection.getProviderName())
            .connected(true)
            .status(status)
            .scopes(List.of(CODEX_SCOPE))
            .expiresAt(connection.getExpiresAt())
            .build();
    }

    private OpenAiCodexOAuthStatusResponse toStatusResponse(OpenAiProviderConnection connection) {
        boolean available = !connection.isExpired(LocalDateTime.now())
            || StringUtils.hasText(connection.getEncryptedRefreshToken());
        return OpenAiCodexOAuthStatusResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .connected(true)
            .available(available)
            .status(available ? "connected" : "expired")
            .accountId(valueOrNull(connection.getMetadata(), "accountId"))
            .expiresAt(connection.getExpiresAt())
            .build();
    }

    private CodexTokenPayload requestToken(MultiValueMap<String, String> form) {
        try {
            Map<String, Object> body = RestClient.create().post()
                .uri(properties.getCodexOAuth().getTokenUrl())
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .body(form)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });

            return parseTokenPayload(body == null ? Map.of() : body);
        } catch (RestClientException exception) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED);
        }
    }

    private CodexTokenPayload parseTokenPayload(Map<String, Object> body) {
        String accessToken = valueAsString(body.get("access_token"));
        if (!StringUtils.hasText(accessToken)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED);
        }

        long expiresIn = valueAsLong(body.get("expires_in"));
        LocalDateTime expiresAt = expiresIn > 0 ? LocalDateTime.now().plusSeconds(expiresIn) : expiresAt(accessToken);
        return new CodexTokenPayload(
            accessToken,
            valueAsString(body.get("refresh_token")),
            expiresAt,
            accountId(valueAsString(body.get("id_token")))
        );
    }

    private MultiValueMap<String, String> formForRefreshToken(String refreshToken) {
        MultiValueMap<String, String> form = baseForm();
        form.add("grant_type", "refresh_token");
        form.add("refresh_token", refreshToken);
        return form;
    }

    private MultiValueMap<String, String> baseForm() {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("client_id", properties.getCodexOAuth().getClientId());
        return form;
    }

    private void validateConfigured() {
        if (!StringUtils.hasText(properties.getCodexOAuth().getClientId())
            || !StringUtils.hasText(properties.getCodexOAuth().getTokenUrl())
            || !properties.hasCredentialEncryptionKey()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
        }
    }

    private String accountId(String idToken) {
        JsonNode payload = tokenPayload(idToken);
        if (payload == null) {
            return null;
        }
        JsonNode auth = payload.get("https://api.openai.com/auth");
        if (auth != null && auth.has("chatgpt_account_id")) {
            return auth.get("chatgpt_account_id").asText();
        }
        return null;
    }

    private LocalDateTime expiresAt(String accessToken) {
        JsonNode payload = tokenPayload(accessToken);
        if (payload == null || !payload.has("exp")) {
            return null;
        }
        return LocalDateTime.ofInstant(
            Instant.ofEpochSecond(payload.get("exp").asLong()),
            ZoneId.systemDefault()
        );
    }

    private JsonNode tokenPayload(String token) {
        if (!StringUtils.hasText(token)) {
            return null;
        }
        String[] parts = token.split("\\.");
        if (parts.length < 2) {
            return null;
        }
        try {
            String payload = new String(Base64.getUrlDecoder().decode(padBase64(parts[1])), StandardCharsets.UTF_8);
            return objectMapper.readTree(payload);
        } catch (Exception exception) {
            return null;
        }
    }

    private String padBase64(String value) {
        int remainder = value.length() % 4;
        if (remainder == 0) {
            return value;
        }
        return value + "=".repeat(4 - remainder);
    }

    private String valueOrNull(Map<String, Object> metadata, String key) {
        if (metadata == null || metadata.get(key) == null) {
            return null;
        }
        return String.valueOf(metadata.get(key));
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }

    private String valueAsString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private long valueAsLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String text && StringUtils.hasText(text)) {
            return Long.parseLong(text);
        }
        return 0;
    }

    private record CodexTokenPayload(
        String accessToken,
        String refreshToken,
        LocalDateTime expiresAt,
        String accountId
    ) {
    }

    public record AccessTokenCredential(String accessToken, LocalDateTime expiresAt) {
    }
}
