package com.ssafy.heygent.domain.ai.openai.service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.LocalDateTime;
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

import com.ssafy.heygent.domain.ai.dto.request.OpenAiOAuthStartRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthStartResponse;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiOAuthTokenPayload;
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
public class OpenAiOAuthService {

    private static final int STATE_TTL_MINUTES = 10;

    private final OpenAiProperties properties;
    private final OpenAiOAuthStateRepository openAiOAuthStateRepository;
    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiCredentialCipher credentialCipher;
    private final SecureRandom secureRandom = new SecureRandom();

    @Transactional
    public OpenAiOAuthStartResponse start(Long userId, OpenAiOAuthStartRequest request) {
        validateOAuthConfigured();

        String redirectUri = StringUtils.hasText(request.getRedirectUri())
            ? request.getRedirectUri().trim()
            : properties.getOauth().getRedirectUri();
        String state = "openai_" + UUID.randomUUID();
        String codeVerifier = codeVerifier();
        String codeChallenge = codeChallenge(codeVerifier);

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
            .scopes(properties.getOauth().getScopes())
            .build();
    }

    @Transactional
    public OpenAiOAuthConnectionResponse complete(String code, String state) {
        validateOAuthConfigured();

        OpenAiOAuthState stateRecord = openAiOAuthStateRepository.findByState(state)
            .filter(record -> record.isPending(LocalDateTime.now()))
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_OAUTH_STATE_INVALID));

        String codeVerifier = credentialCipher.decrypt(stateRecord.getEncryptedCodeVerifier());
        OpenAiOAuthTokenPayload tokenPayload = requestToken(formForAuthorizationCode(
            code,
            stateRecord.getRedirectUri(),
            codeVerifier
        ));
        OpenAiProviderConnection connection = upsertConnection(stateRecord.getUserId(), tokenPayload);
        stateRecord.consume(LocalDateTime.now());

        return toConnectionResponse(connection, "connected");
    }

    @Transactional
    public OpenAiOAuthConnectionResponse refresh(Long userId) {
        OpenAiProviderConnection connection = getConnection(userId);
        String refreshToken = credentialCipher.decrypt(connection.getEncryptedRefreshToken());
        if (!StringUtils.hasText(refreshToken)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED);
        }

        OpenAiOAuthTokenPayload tokenPayload = requestToken(formForRefreshToken(refreshToken));
        OpenAiProviderConnection updated = upsertConnection(userId, tokenPayload);
        return toConnectionResponse(updated, "refreshed");
    }

    @Transactional
    public OpenAiOAuthConnectionResponse disconnect(Long userId) {
        openAiProviderConnectionRepository.deleteByUserIdAndProviderName(
            userId,
            OpenAiProviderName.OPENAI_OAUTH.getValue()
        );
        return OpenAiOAuthConnectionResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_OAUTH.getValue())
            .connected(false)
            .status("disconnected")
            .scopes(List.of())
            .expiresAt(null)
            .build();
    }

    @Transactional
    public String resolveAccessToken(Long userId) {
        OpenAiProviderConnection connection = getConnection(userId);
        if (connection.isExpired(LocalDateTime.now()) && StringUtils.hasText(connection.getEncryptedRefreshToken())) {
            refresh(userId);
            connection = getConnection(userId);
        }
        if (connection.isExpired(LocalDateTime.now())) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED);
        }
        return credentialCipher.decrypt(connection.getEncryptedAccessToken());
    }

    private OpenAiProviderConnection getConnection(Long userId) {
        return openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_OAUTH.getValue())
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_OAUTH_NOT_CONNECTED));
    }

    private OpenAiProviderConnection upsertConnection(Long userId, OpenAiOAuthTokenPayload tokenPayload) {
        OpenAiProviderConnection connection = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_OAUTH.getValue())
            .orElseGet(() -> OpenAiProviderConnection.builder()
                .userId(userId)
                .providerName(OpenAiProviderName.OPENAI_OAUTH.getValue())
                .build());

        String refreshToken = StringUtils.hasText(tokenPayload.refreshToken())
            ? tokenPayload.refreshToken()
            : credentialCipher.decrypt(connection.getEncryptedRefreshToken());
        connection.updateToken(
            tokenPayload.tokenType(),
            credentialCipher.encrypt(tokenPayload.accessToken()),
            credentialCipher.encrypt(refreshToken),
            String.join(",", tokenPayload.scopes()),
            tokenPayload.expiresAt(),
            tokenPayload.rawPayload()
        );
        return openAiProviderConnectionRepository.save(connection);
    }

    private OpenAiOAuthConnectionResponse toConnectionResponse(OpenAiProviderConnection connection, String status) {
        return OpenAiOAuthConnectionResponse.builder()
            .providerName(connection.getProviderName())
            .connected(true)
            .status(status)
            .scopes(parseScopes(connection.getScopeText()))
            .expiresAt(connection.getExpiresAt())
            .build();
    }

    private OpenAiOAuthTokenPayload requestToken(MultiValueMap<String, String> form) {
        try {
            Map<String, Object> body = RestClient.create().post()
                .uri(properties.getOauth().getTokenUrl())
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

    private OpenAiOAuthTokenPayload parseTokenPayload(Map<String, Object> body) {
        String accessToken = valueAsString(body.get("access_token"));
        if (!StringUtils.hasText(accessToken)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED);
        }

        long expiresIn = valueAsLong(body.get("expires_in"));
        return new OpenAiOAuthTokenPayload(
            accessToken,
            valueAsString(body.get("refresh_token")),
            StringUtils.hasText(valueAsString(body.get("token_type"))) ? valueAsString(body.get("token_type")) : "Bearer",
            resolveScopes(valueAsString(body.get("scope"))),
            expiresIn > 0 ? LocalDateTime.now().plusSeconds(expiresIn) : null,
            body
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
        form.add("client_id", properties.getOauth().getClientId());
        if (StringUtils.hasText(properties.getOauth().getClientSecret())) {
            form.add("client_secret", properties.getOauth().getClientSecret());
        }
        return form;
    }

    private String authorizationUrl(String redirectUri, String state, String codeChallenge) {
        return properties.getOauth().getAuthorizeUrl()
            + "?response_type=code"
            + "&client_id=" + urlEncode(properties.getOauth().getClientId())
            + "&redirect_uri=" + urlEncode(redirectUri)
            + "&scope=" + urlEncode(String.join(" ", properties.getOauth().getScopes()))
            + "&code_challenge=" + urlEncode(codeChallenge)
            + "&code_challenge_method=S256"
            + "&state=" + urlEncode(state);
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

    private void validateOAuthConfigured() {
        if (!StringUtils.hasText(properties.getOauth().getClientId())
            || !StringUtils.hasText(properties.getOauth().getAuthorizeUrl())
            || !StringUtils.hasText(properties.getOauth().getTokenUrl())
            || !properties.hasCredentialEncryptionKey()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
        }
    }

    private List<String> resolveScopes(String scopeText) {
        if (!StringUtils.hasText(scopeText)) {
            return properties.getOauth().getScopes();
        }
        return parseScopes(scopeText.replace(" ", ","));
    }

    private List<String> parseScopes(String scopeText) {
        if (!StringUtils.hasText(scopeText)) {
            return List.of();
        }
        return List.of(scopeText.split(",")).stream()
            .map(String::trim)
            .filter(StringUtils::hasText)
            .toList();
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
}
