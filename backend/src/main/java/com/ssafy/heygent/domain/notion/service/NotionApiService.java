package com.ssafy.heygent.domain.notion.service;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class NotionApiService {

    private static final Logger log = LoggerFactory.getLogger(NotionApiService.class);
    private static final String PROXY_URL = "https://backend.composio.dev/api/v3.1/tools/execute/proxy";
    private static final String NOTION_VERSION = "2022-06-28";

    private final ComposioService composioService;
    private final ObjectMapper objectMapper;

    @Value("${composio.api-key}")
    private String composioApiKey;

    private final RestTemplate restTemplate = Utf8RestTemplateFactory.create();

    public Map createPage(Long userId, Map<String, Object> params) {
        return proxy(userId, "POST", "/v1/pages", params);
    }

    public Map getPage(Long userId, String pageId) {
        return proxy(userId, "GET", "/v1/pages/" + pageId, null);
    }

    public Map getPageBlocks(Long userId, String pageId) {
        return proxy(userId, "GET", "/v1/blocks/" + pageId + "/children", null);
    }

    public Map updatePage(Long userId, String pageId, Map<String, Object> params) {
        return proxy(userId, "PATCH", "/v1/pages/" + pageId, params);
    }

    public Map appendBlocks(Long userId, String blockId, Map<String, Object> params) {
        return proxy(userId, "PATCH", "/v1/blocks/" + blockId + "/children", params);
    }

    public Map queryDatabase(Long userId, String databaseId, Map<String, Object> params) {
        return proxy(userId, "POST", "/v1/databases/" + databaseId + "/query", params);
    }

    public Map insertDatabaseRow(Long userId, Map<String, Object> params) {
        return proxy(userId, "POST", "/v1/pages", params);
    }

    public Map search(Long userId, Map<String, Object> params) {
        return proxy(userId, "POST", "/v1/search", params);
    }

    private Map proxy(Long userId, String method, String notionPath, Map<String, Object> body) {
        String connectedAccountId = composioService.getConnectedAccountId(userId);

        Map<String, Object> requestBody = new java.util.HashMap<>();
        requestBody.put("connected_account_id", connectedAccountId);
        requestBody.put("method", method);
        requestBody.put("endpoint", notionPath);
        requestBody.put("parameters", List.of(
            Map.of("name", "Notion-Version", "value", NOTION_VERSION, "type", "header")
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
            if (response == null) throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);

            Integer status = (Integer) response.get("status");
            if (status != null && status >= 400) {
                log.error("[Notion proxy] 오류 응답 - path: {}, status: {}, data: {}", notionPath, status, response.get("data"));
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            return (Map) response.get("data");
        } catch (HttpClientErrorException e) {
            log.error("[Notion proxy] HTTP 오류 - path: {}, status: {}, body: {}", notionPath, e.getStatusCode(), e.getResponseBodyAsString());
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
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
}
