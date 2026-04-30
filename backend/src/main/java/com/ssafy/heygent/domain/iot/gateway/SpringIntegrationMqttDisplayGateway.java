package com.ssafy.heygent.domain.iot.gateway;

import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.integration.mqtt.support.MqttHeaders;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "iot.mqtt", name = "enabled", havingValue = "true")
public class SpringIntegrationMqttDisplayGateway implements MqttDisplayGateway {

    private final MessageChannel mqttOutboundChannel;

    @Override
    public void publish(String topic, String payload, int qos) {
        Message<String> message = MessageBuilder.withPayload(payload)
            .setHeader(MqttHeaders.TOPIC, topic)
            .setHeader(MqttHeaders.QOS, qos)
            .build();

        boolean sent = mqttOutboundChannel.send(message);
        if (!sent) {
            throw new IllegalStateException("Failed to send MQTT display message to outbound channel.");
        }
    }
}
