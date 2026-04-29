package com.ssafy.heygent.domain.iot.gateway;

public class SpringIntegrationMqttDisplayGateway {

    /*
     * 나중에 MqttDisplayGateway의 실제 Spring Integration 기반 구현체로 바꿀 클래스다.
     *
     * 예상 구현:
     * - MessageChannel mqttOutboundChannel 주입
     * - MqttHeaders.TOPIC, MqttHeaders.QOS를 세팅해 publish
     * - IOT_MQTT_ENABLED=true일 때만 Bean으로 등록
     */
}
