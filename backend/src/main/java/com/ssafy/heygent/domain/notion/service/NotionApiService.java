package com.ssafy.heygent.domain.notion.service;

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
import com.ssafy.heygent.domain.notion.dto.request.NotionExecuteCommandRequest;
import com.ssafy.heygent.domain.notion.dto.response.NotionExecuteCommandResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class NotionApiService {

    private static final Logger log = LoggerFactory.getLogger(NotionApiService.class);
    private static final String PROXY_URL = "https://backend.composio.dev/api/v3.1/tools/execute/proxy";
    private static final String DEFAULT_NOTION_VERSION = "2022-06-28";
    private static final Set<String> SUPPORTED_METHODS = Set.of("GET", "POST", "PATCH", "DELETE");

    private final ComposioService composioService;
    private final ObjectMapper objectMapper;

    @Value("${composio.api-key}")
    private String composioApiKey;

    private final RestTemplate restTemplate = Utf8RestTemplateFactory.create();

    public List<NotionExecuteCommandResponse> executeBatch(
        Long authenticatedUserId,
        Long requestUserId,
        List<NotionExecuteCommandRequest> commands
    ) {
        validateUserId(authenticatedUserId, requestUserId);

        List<NotionExecuteCommandResponse> results = new ArrayList<>();
        for (int index = 0; index < commands.size(); index++) {
            results.add(executeCommand(requestUserId, index, commands.get(index)));
        }
        return results;
    }

    public Map executeProxy(Long userId, String method, String endpoint, Map<String, Object> params, String notionVersion) {
        String normalizedMethod = normalizeMethod(method);
        String normalizedEndpoint = normalizeEndpoint(endpoint);
        return proxy(userId, normalizedMethod, normalizedEndpoint, params, notionVersion);
    }

    private Map proxy(Long userId, String method, String notionPath, Map<String, Object> body, String notionVersion) {
        String connectedAccountId = composioService.getConnectedAccountId(userId);
        String resolvedVersion = resolveNotionVersion(notionVersion);

        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("connected_account_id", connectedAccountId);
        requestBody.put("method", method);
        requestBody.put("endpoint", notionPath);
        requestBody.put("parameters", List.of(
            Map.of("name", "Notion-Version", "value", resolvedVersion, "type", "header")
        ));
        if (body != null) {
            requestBody.put("body", body);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.set("x-api-key", composioApiKey);
        headers.setContentType(new MediaType(MediaType.APPLICATION_JSON, StandardCharsets.UTF_8));
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.setAcceptCharset(List.of(StandardCharsets.UTF_8));

        try {
            logProxyRequest(method, notionPath, requestBody);
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
                log.error("[Notion proxy] error response - path: {}, status: {}, data: {}", notionPath, status, response.get("data"));
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            return (Map) response.get("data");
        } catch (HttpClientErrorException e) {
            log.error("[Notion proxy] HTTP error - path: {}, status: {}, body: {}", notionPath, e.getStatusCode(), e.getResponseBodyAsString());
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    private NotionExecuteCommandResponse executeCommand(Long userId, int index, NotionExecuteCommandRequest command) {
        String method = normalizeNullable(command.getMethod());
        String endpoint = normalizeNullable(command.getEndpoint());
        String notionVersion = resolveNotionVersion(command.getNotionVersion());

        try {
            Map data = executeProxy(userId, command.getMethod(), command.getEndpoint(), command.getParams(), command.getNotionVersion());
            return NotionExecuteCommandResponse.success(index, userId, method, endpoint, notionVersion, data);
        } catch (CustomException e) {
            return NotionExecuteCommandResponse.failure(
                index,
                userId,
                method,
                endpoint,
                notionVersion,
                e.getErrorCode().name(),
                e.getErrorCode().getMessage()
            );
        } catch (Exception e) {
            log.error("[Notion proxy] unexpected batch execution error - index: {}, endpoint: {}", index, endpoint, e);
            return NotionExecuteCommandResponse.failure(
                index,
                userId,
                method,
                endpoint,
                notionVersion,
                ErrorCode.INTERNAL_SERVER_ERROR.name(),
                ErrorCode.INTERNAL_SERVER_ERROR.getMessage()
            );
        }
    }

    private void logProxyRequest(String method, String notionPath, Map<String, Object> requestBody) {
        try {
            String payload = objectMapper.writeValueAsString(requestBody);
            boolean hasNonAscii = payload.chars().anyMatch(character -> character > 127);
            log.info(
                "[Notion proxy] request - method: {}, path: {}, hasNonAscii: {}, utf8Bytes: {}, payloadPreview: {}",
                method,
                notionPath,
                hasNonAscii,
                payload.getBytes(StandardCharsets.UTF_8).length,
                abbreviate(payload, 500)
            );
        } catch (JsonProcessingException e) {
            log.warn("[Notion proxy] failed to serialize request body for logging - path: {}", notionPath, e);
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
        if (!normalizedEndpoint.startsWith("/v1/")) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return normalizedEndpoint;
    }

    private String resolveNotionVersion(String notionVersion) {
        if (!StringUtils.hasText(notionVersion)) {
            return DEFAULT_NOTION_VERSION;
        }
        return notionVersion.trim();
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
