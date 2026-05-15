package com.ssafy.heygent.domain.gmail.service;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.gmail.dto.request.GmailExecuteCommandRequest;
import com.ssafy.heygent.domain.gmail.dto.response.GmailExecuteCommandResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class GmailApiService {

    private static final Logger log = LoggerFactory.getLogger(GmailApiService.class);
    private static final String PROXY_URL = "https://backend.composio.dev/api/v3.1/tools/execute/proxy";
    private static final Set<String> SUPPORTED_METHODS = Set.of("GET", "POST", "PUT", "PATCH", "DELETE");
    private static final String GMAIL_PATH_PREFIX = "/gmail/v1/";

    private final GmailComposioService gmailComposioService;
    private final ObjectMapper objectMapper;

    @Value("${composio.api-key}")
    private String composioApiKey;

    private final RestTemplate restTemplate = GmailUtf8RestTemplateFactory.create();

    public List<GmailExecuteCommandResponse> executeBatch(
        Long authenticatedUserId,
        Long requestUserId,
        List<GmailExecuteCommandRequest> commands
    ) {
        validateUserId(authenticatedUserId, requestUserId);

        List<GmailExecuteCommandResponse> results = new ArrayList<>();
        for (int index = 0; index < commands.size(); index++) {
            results.add(executeCommand(requestUserId, index, commands.get(index)));
        }
        return results;
    }

    public Map executeProxy(Long userId, String method, String endpoint, Map<String, Object> params) {
        String normalizedMethod = normalizeMethod(method);
        String normalizedEndpoint = normalizeEndpoint(endpoint);
        return proxy(userId, normalizedMethod, normalizedEndpoint, params);
    }

    private Map proxy(Long userId, String method, String gmailPath, Map<String, Object> body) {
        String connectedAccountId = gmailComposioService.getConnectedAccountId(userId);

        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("connected_account_id", connectedAccountId);
        requestBody.put("method", method);
        requestBody.put("endpoint", gmailPath);
        if (body != null) {
            requestBody.put("body", body);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.set("x-api-key", composioApiKey);
        headers.setContentType(new MediaType(MediaType.APPLICATION_JSON, StandardCharsets.UTF_8));
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.setAcceptCharset(List.of(StandardCharsets.UTF_8));

        try {
            logProxyRequest(method, gmailPath, requestBody);
            Map response = restTemplate.postForObject(
                PROXY_URL,
                new HttpEntity<>(requestBody, headers),
                Map.class
            );
            if (response == null) {
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            Integer status = (Integer) response.get("status");
            if (status != null && status >= 400) {
                log.error("[Gmail proxy] error response - path: {}, status: {}, data: {}", gmailPath, status, response.get("data"));
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            return (Map) response.get("data");
        } catch (HttpClientErrorException e) {
            log.error("[Gmail proxy] HTTP error - path: {}, status: {}, body: {}", gmailPath, e.getStatusCode(), e.getResponseBodyAsString());
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    private GmailExecuteCommandResponse executeCommand(Long userId, int index, GmailExecuteCommandRequest command) {
        String method = normalizeNullable(command.getMethod());
        String endpoint = normalizeNullable(command.getEndpoint());

        try {
            Map data = executeProxy(userId, command.getMethod(), command.getEndpoint(), command.getParams());
            return GmailExecuteCommandResponse.success(index, userId, method, endpoint, data);
        } catch (CustomException e) {
            return GmailExecuteCommandResponse.failure(
                index,
                userId,
                method,
                endpoint,
                e.getErrorCode().name(),
                e.getErrorCode().getMessage()
            );
        } catch (Exception e) {
            log.error("[Gmail proxy] unexpected batch execution error - index: {}, endpoint: {}", index, endpoint, e);
            return GmailExecuteCommandResponse.failure(
                index,
                userId,
                method,
                endpoint,
                ErrorCode.INTERNAL_SERVER_ERROR.name(),
                ErrorCode.INTERNAL_SERVER_ERROR.getMessage()
            );
        }
    }

    private void logProxyRequest(String method, String gmailPath, Map<String, Object> requestBody) {
        try {
            String payload = objectMapper.writeValueAsString(requestBody);
            boolean hasNonAscii = payload.chars().anyMatch(character -> character > 127);
            log.info(
                "[Gmail proxy] request - method: {}, path: {}, hasNonAscii: {}, utf8Bytes: {}, payloadPreview: {}",
                method,
                gmailPath,
                hasNonAscii,
                payload.getBytes(StandardCharsets.UTF_8).length,
                abbreviate(payload, 500)
            );
        } catch (JsonProcessingException e) {
            log.warn("[Gmail proxy] failed to serialize request body for logging - path: {}", gmailPath, e);
        }
    }

    private String abbreviate(String text, int maxLength) {
        if (text == null || text.length() <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + "...";
    }

    private String normalizeMethod(String method) {
        if (!StringUtils.hasText(method)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        String normalizedMethod = method.trim().toUpperCase(Locale.ROOT);
        if (!SUPPORTED_METHODS.contains(normalizedMethod)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return normalizedMethod;
    }

    private String normalizeEndpoint(String endpoint) {
        if (!StringUtils.hasText(endpoint)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        String normalizedEndpoint = endpoint.trim();
        if (!normalizedEndpoint.startsWith(GMAIL_PATH_PREFIX)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return normalizedEndpoint;
    }

    private void validateUserId(Long authenticatedUserId, Long requestUserId) {
        if (requestUserId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        if (!requestUserId.equals(authenticatedUserId)) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }
    }

    private String normalizeNullable(String value) {
        return value == null ? null : value.trim();
    }
}
