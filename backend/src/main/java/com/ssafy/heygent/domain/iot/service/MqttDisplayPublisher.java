package com.ssafy.heygent.domain.iot.service;

public class MqttDisplayPublisher {

    /*
     * 나중에 DisplayEventPayload를 MQTT Broker로 publish하는 application service다.
     *
     * 예상 역할:
     * - deviceId를 devices/{deviceId}/display topic으로 변환
     * - DisplayEventPayload를 JSON으로 직렬화
     * - STARTED/STEP은 QoS 0, WAITING/DONE/FAILED는 QoS 1로 선택
     * - MqttDisplayGateway를 호출해 실제 publish 수행
     * - MQTT disabled 상태에서는 publish를 skip하고 로그만 남김
     */
}
