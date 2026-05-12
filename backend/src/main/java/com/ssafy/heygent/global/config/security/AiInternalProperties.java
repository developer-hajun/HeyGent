package com.ssafy.heygent.global.config.security;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "ai.internal")
public class AiInternalProperties {

    private String token;
    /**
     * AI 서버의 "현재 WebSocket 으로 붙어있는 브릿지 user_id 목록" 조회 URL.
     * 컨테이너 안에서 통신하므로 service 이름 기반. 환경별 .env 로 override 가능.
     */
    private String onlineUsersUrl;
}
