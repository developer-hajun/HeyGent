package com.ssafy.heygent.domain.ai.openai.service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.util.UriComponentsBuilder;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.ai.dto.request.OpenAiCodexOAuthCompleteRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCodexOAuthStatusResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthStartResponse;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiOAuthState;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiOAuthStateStatus;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiOAuthStateRepository;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;
import com.ssafy.heygent.domain.ai.openai.security.OpenAiCredentialCipher;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiCodexOAuthService {

    private static final int STATE_TTL_MINUTES = 10;
    private static final String CODEX_SCOPE = "codex";
    private static final String TOKEN_TYPE = "Bearer";

    private final OpenAiProperties properties;
    private final OpenAiOAuthStateRepository openAiOAuthStateRepository;
    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiCredentialCipher credentialCipher;
    private final ObjectMapper objectMapper;
    private final SecureRandom secureRandom = new SecureRandom();

    @Transactional
    public OpenAiOAuthStartResponse start(Long userId) {
        validateConfigured();

        String state = "codex_" + UUID.randomUUID();
        String codeVerifier = codeVerifier();
        String codeChallenge = codeChallenge(codeVerifier);
        String redirectUri = properties.getCodexOAuth().getRedirectUri();

        openAiOAuthStateRepository.save(OpenAiOAuthState.builder()
            .state(state)
            .userId(userId)
            .redirectUri(redirectUri)
            .encryptedCodeVerifier(credentialCipher.encrypt(codeVerifier))
            .status(OpenAiOAuthStateStatus.PENDING)
            .expiresAt(LocalDateTime.now().plusMinutes(STATE_TTL_MINUTES))
            .build());

        return OpenAiOAuthStartResponse.builder()
            .status("authorization_required")
            .authorizationUrl(authorizationUrl(redirectUri, state, codeChallenge))
            .state(state)
            .redirectUri(redirectUri)
            .scopes(properties.getCodexOAuth().getScopes())
            .build();
    }

    @Transactional
    public OpenAiOAuthConnectionResponse complete(String code, String state) {
        validateConfigured();
        if (!StringUtils.hasText(state) || !state.startsWith("codex_")) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_STATE_INVALID);
        }

        OpenAiOAuthState stateRecord = openAiOAuthStateRepository.findByState(state)
            .filter(record -> record.isPending(LocalDateTime.now()))
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_OAUTH_STATE_INVALID));

        String codeVerifier = credentialCipher.decrypt(stateRecord.getEncryptedCodeVerifier());
        CodexTokenPayload tokenPayload = requestToken(formForAuthorizationCode(
            code,
            stateRecord.getRedirectUri(),
            codeVerifier
        ));
        OpenAiProviderConnection connection = upsertConnection(stateRecord.getUserId(), tokenPayload);
        stateRecord.consume(LocalDateTime.now());

        return toConnectionResponse(connection, "connected");
    }

    @Transactional
    public OpenAiOAuthConnectionResponse complete(OpenAiCodexOAuthCompleteRequest request) {
        CompletionParams params = completionParams(request);
        return complete(params.code(), params.state());
    }

    @Transactional
    public OpenAiOAuthConnectionResponse refresh(Long userId) {
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
        connection.updateToken(
            TOKEN_TYPE,
            credentialCipher.encrypt(tokenPayload.accessToken()),
            credentialCipher.encrypt(refreshToken),
            CODEX_SCOPE,
            tokenPayload.expiresAt(),
            Map.of(
                "accountId", valueOrEmpty(tokenPayload.accountId()),
                "credentialFormat", "codex_oauth",
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

    private CompletionParams completionParams(OpenAiCodexOAuthCompleteRequest request) {
        if (request == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        if (StringUtils.hasText(request.getRedirectUrl())) {
            return completionParamsFromRedirectUrl(request.getRedirectUrl());
        }

        if (StringUtils.hasText(request.getCode()) && StringUtils.hasText(request.getState())) {
            return new CompletionParams(request.getCode().trim(), request.getState().trim());
        }

        throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
    }

    private CompletionParams completionParamsFromRedirectUrl(String redirectUrl) {
        try {
            var queryParams = UriComponentsBuilder.fromUriString(redirectUrl.trim())
                .build()
                .getQueryParams();
            String code = queryParams.getFirst("code");
            String state = queryParams.getFirst("state");
            if (!StringUtils.hasText(code) || !StringUtils.hasText(state)) {
                throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
            }
            return new CompletionParams(code.trim(), state.trim());
        } catch (CustomException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
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

    private MultiValueMap<String, String> formForAuthorizationCode(
        String code,
        String redirectUri,
        String codeVerifier
    ) {
        MultiValueMap<String, String> form = baseForm();
        form.add("grant_type", "authorization_code");
        form.add("code", code);
        form.add("redirect_uri", redirectUri);
        form.add("code_verifier", codeVerifier);
        return form;
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

    private String authorizationUrl(String redirectUri, String state, String codeChallenge) {
        return properties.getCodexOAuth().getAuthorizeUrl()
            + "?response_type=code"
            + "&client_id=" + urlEncode(properties.getCodexOAuth().getClientId())
            + "&redirect_uri=" + urlEncode(redirectUri)
            + "&scope=" + urlEncode(String.join(" ", properties.getCodexOAuth().getScopes()))
            + "&code_challenge=" + urlEncode(codeChallenge)
            + "&code_challenge_method=S256"
            + "&state=" + urlEncode(state)
            + "&id_token_add_organizations=true"
            + "&codex_cli_simplified_flow=true"
            + "&originator=openclaw";
    }

    private void validateConfigured() {
        if (!StringUtils.hasText(properties.getCodexOAuth().getClientId())
            || !StringUtils.hasText(properties.getCodexOAuth().getRedirectUri())
            || !StringUtils.hasText(properties.getCodexOAuth().getAuthorizeUrl())
            || !StringUtils.hasText(properties.getCodexOAuth().getTokenUrl())
            || !properties.hasCredentialEncryptionKey()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
        }
    }

    private String codeVerifier() {
        byte[] bytes = new byte[64];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String codeChallenge(String verifier) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(digest);
        } catch (Exception exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
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

    private String urlEncode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
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

    private record CompletionParams(String code, String state) {
    }
}
