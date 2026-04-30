package com.ssafy.heygent.domain.iot.gateway;

public interface MqttDisplayGateway {

    void publish(String topic, String payload, int qos);
}
