package com.ssafy.heygent.domain.iot.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.iot.config.MqttProperties;
import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.gateway.MqttDisplayGateway;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Slf4j
@Service
@RequiredArgsConstructor
public class MqttDisplayPublisher {

    private static final String DISPLAY_TOPIC_SUFFIX = "display";
    private static final String DEFAULT_TOPIC_PREFIX = "devices";

    private final MqttProperties properties;
    private final ObjectProvider<MqttDisplayGateway> mqttDisplayGatewayProvider;
    private final ObjectMapper objectMapper;

    public DisplayPublishResult publish(String deviceId, DisplayEventPayload payload) {
        String topic = buildTopic(deviceId);
        int qos = resolveQos(payload.type());

        if (!properties.isEnabled()) {
            return DisplayPublishResult.skipped("MQTT disabled", topic, qos, payload);
        }

        MqttDisplayGateway gateway = mqttDisplayGatewayProvider.getIfAvailable();
        if (gateway == null) {
            return DisplayPublishResult.skipped("MQTT gateway unavailable", topic, qos, payload);
        }

        try {
            String jsonPayload = objectMapper.writeValueAsString(payload);
            gateway.publish(topic, jsonPayload, qos);
            return DisplayPublishResult.published(topic, qos, payload);
        } catch (JsonProcessingException exception) {
            log.warn("Failed to serialize MQTT display payload.", exception);
            return DisplayPublishResult.skipped("MQTT payload serialization failed", topic, qos, payload);
        } catch (RuntimeException exception) {
            log.warn("Failed to publish MQTT display payload. topic={}, qos={}", topic, qos, exception);
            return DisplayPublishResult.skipped("MQTT publish failed", topic, qos, payload);
        }
    }

    private String buildTopic(String deviceId) {
        String topicPrefix = StringUtils.hasText(properties.getTopicPrefix())
            ? properties.getTopicPrefix()
            : DEFAULT_TOPIC_PREFIX;

        return trimSlashes(topicPrefix) + "/" + trimSlashes(deviceId) + "/" + DISPLAY_TOPIC_SUFFIX;
    }

    private int resolveQos(DisplayEventType type) {
        return switch (type) {
            case WAITING, DONE, FAILED, CANCELED -> 1;
            case STARTED, STEP, INFO -> normalizeQos(properties.getDefaultQos());
        };
    }

    private int normalizeQos(int qos) {
        return Math.max(0, Math.min(2, qos));
    }

    private String trimSlashes(String value) {
        String trimmed = value.trim();
        while (trimmed.startsWith("/")) {
            trimmed = trimmed.substring(1);
        }
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed;
    }
}
