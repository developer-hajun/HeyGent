package com.ssafy.heygent.domain.notion.service;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@Service
public class ComposioService {

    private static final Logger log = LoggerFactory.getLogger(ComposioService.class);
    private static final String BASE_URL = "https://backend.composio.dev/api/v3";

    @Value("${composio.api-key}")
    private String apiKey;

    @Value("${composio.notion.redirect-uri}")
    private String redirectUri;

    @Value("${composio.notion.integration-id}")
    private String integrationId;

    private final RestTemplate restTemplate = Utf8RestTemplateFactory.create();

    // Notion 연결 URL 생성
    public String getNotionConnectUrl(Long userId) {
        HttpHeaders headers = buildHeaders();
        Map<String, Object> body = Map.of(
            "auth_config", Map.of("id", integrationId),
            "connection", Map.of(
                "user_id", userId.toString(),
                "redirect_uri", redirectUri
            )
        );

        try {
            log.info("[Composio] 연결 URL 요청 - userId: {}, body: {}", userId, body);
            Map response = restTemplate.postForObject(
                BASE_URL + "/connected_accounts",
                new HttpEntity<>(body, headers),
                Map.class
            );
            log.info("[Composio] 응답: {}", response);
            // v3: redirect_url 또는 redirectUrl 둘 다 시도
            String redirectUrl = response.get("redirect_url") != null
                ? response.get("redirect_url").toString()
                : response.get("redirectUrl") != null
                    ? response.get("redirectUrl").toString()
                    : null;
            if (redirectUrl == null) {
                log.error("[Composio] redirect_url 없음. 전체 응답: {}", response);
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }
            return redirectUrl;
        } catch (HttpClientErrorException e) {
            log.error("[Composio] HTTP 에러 - status: {}, body: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            log.error("[Composio] 예외 발생: {}", e.getMessage(), e);
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    // Notion 연결 상태 확인
    public boolean isNotionConnected(Long userId) {
        HttpHeaders headers = buildHeaders();
        try {
            Map response = restTemplate.exchange(
                BASE_URL + "/connected_accounts?user_ids=" + userId + "&auth_config_ids=" + integrationId + "&statuses=ACTIVE",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                Map.class
            ).getBody();

            log.info("[Composio] 연결 상태 응답: {}", response);
            if (response == null) return false;
            List<Map> items = (List<Map>) response.get("items");
            return items != null && !items.isEmpty();
        } catch (Exception e) {
            log.error("[Composio] 연결 상태 확인 실패: {}", e.getMessage());
            return false;
        }
    }

    // Notion 연결 해제
    public void disconnectNotion(Long userId) {
        HttpHeaders headers = buildHeaders();
        try {
            Map response = restTemplate.exchange(
                BASE_URL + "/connected_accounts?user_ids=" + userId + "&auth_config_ids=" + integrationId + "&statuses=ACTIVE",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                Map.class
            ).getBody();

            if (response == null) return;
            List<Map> items = (List<Map>) response.get("items");
            if (items == null || items.isEmpty()) return;

            String connectionId = items.get(0).get("id").toString();
            restTemplate.exchange(
                BASE_URL + "/connected_accounts/" + connectionId,
                HttpMethod.DELETE,
                new HttpEntity<>(headers),
                Map.class
            );
        } catch (Exception e) {
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    // Notion connected account ID 조회 (Composio proxy 호출 시 사용)
    public String getConnectedAccountId(Long userId) {
        HttpHeaders headers = buildHeaders();
        try {
            Map response = restTemplate.exchange(
                BASE_URL + "/connected_accounts?user_ids=" + userId + "&auth_config_ids=" + integrationId + "&statuses=ACTIVE",
                HttpMethod.GET,
                new HttpEntity<>(headers),
                Map.class
            ).getBody();

            if (response == null) throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
            List<Map> items = (List<Map>) response.get("items");
            if (items == null || items.isEmpty()) throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);

            Object id = items.get(0).get("id");
            if (id == null) throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
            return id.toString();
        } catch (CustomException e) {
            throw e;
        } catch (Exception e) {
            log.error("[Composio] connected_account_id 조회 실패: {}", e.getMessage());
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    private HttpHeaders buildHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.set("x-api-key", apiKey);
        headers.setContentType(new MediaType(MediaType.APPLICATION_JSON, StandardCharsets.UTF_8));
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
        headers.setAcceptCharset(List.of(StandardCharsets.UTF_8));
        return headers;
    }
}
