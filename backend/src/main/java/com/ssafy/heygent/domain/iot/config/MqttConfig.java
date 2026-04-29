package com.ssafy.heygent.domain.iot.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(MqttProperties.class)
public class MqttConfig {

    /*
     * local, 서버 분리 필요cq
     * 현재 단계에서는 env 값을 MqttProperties로 바인딩하는 역할만 한다.
     *
     * 나중에 MQTT publish를 실제로 붙일 때 추가할 내용:
     * - MQTT client factory Bean
     * - outbound MessageChannel Bean
     * - MQTT outbound MessageHandler Bean
     * - IOT_MQTT_ENABLED=true일 때만 broker에 연결되도록 조건부 Bean 구성
     */
}
