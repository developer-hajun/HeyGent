package com.ssafy.heygent.domain.bridge.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.ssafy.heygent.global.config.security.AiInternalProperties;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestTemplate;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * AI 서버에 "현재 WebSocket 으로 붙어있는 브릿지 user_id 목록" 을 묻는 클라이언트.
 * 디바이스 목록 응답에 online 여부를 채우기 위해 사용한다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AiBridgeStatusClient {

    private final AiInternalProperties aiInternalProperties;
    private final RestTemplate restTemplate = new RestTemplate();

    public Set<Long> fetchOnlineUserIds() {
        String url = aiInternalProperties.getOnlineUsersUrl();
        String token = aiInternalProperties.getToken();
        if (!StringUtils.hasText(url) || !StringUtils.hasText(token)) {
            return Collections.emptySet();
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(token);
        HttpEntity<Void> request = new HttpEntity<>(headers);

        try {
            ResponseEntity<JsonNode> response =
                restTemplate.exchange(url, HttpMethod.GET, request, JsonNode.class);
            JsonNode body = response.getBody();
            if (body == null) {
                return Collections.emptySet();
            }
            JsonNode userIds = body.path("userIds");
            if (!userIds.isArray()) {
                return Collections.emptySet();
            }
            Set<Long> result = new HashSet<>();
            for (JsonNode node : userIds) {
                if (node.isNumber()) {
                    result.add(node.asLong());
                } else if (node.isTextual()) {
                    try {
                        result.add(Long.parseLong(node.asText()));
                    } catch (NumberFormatException ignored) {
                        // AI 서버가 user_id 를 문자열로도 보낼 수 있다.
                    }
                }
            }
            return result;
        } catch (Exception exception) {
            // 온라인 상태 조회는 부수 정보이므로 실패해도 디바이스 목록은 그대로 내려준다.
            log.warn("AI 서버 온라인 user 조회 실패: {}", exception.getMessage());
            return Collections.emptySet();
        }
    }
}
