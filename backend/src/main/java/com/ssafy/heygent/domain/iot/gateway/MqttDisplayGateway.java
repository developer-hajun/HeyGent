package com.ssafy.heygent.domain.iot.gateway;

public class MqttDisplayGateway {

    /*
     * 나중에 Spring 내부 서비스가 MQTT Broker로 display payload를 보낼 때 사용할 발행 통로다.
     *
     * 예상 역할:
     * - topic과 JSON payload를 받아 MQTT outbound channel로 전달
     * - Spring Integration MQTT 또는 Paho client 구현체로 연결
     * - FastAPI 연동 후 Spring이 display event를 publish할 때 사용
     */
}
