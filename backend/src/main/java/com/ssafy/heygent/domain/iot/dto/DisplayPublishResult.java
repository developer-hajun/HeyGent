package com.ssafy.heygent.domain.iot.dto;

public record DisplayPublishResult(
    boolean published,
    String topic,
    int qos,
    DisplayEventPayload payload,
    String reason
) {

    public static DisplayPublishResult published(String topic, int qos, DisplayEventPayload payload) {
        return new DisplayPublishResult(true, topic, qos, payload, null);
    }

    public static DisplayPublishResult skipped(String reason, DisplayEventPayload payload) {
        return new DisplayPublishResult(false, null, 0, payload, reason);
    }

    public static DisplayPublishResult skipped(String reason, String topic, int qos, DisplayEventPayload payload) {
        return new DisplayPublishResult(false, topic, qos, payload, reason);
    }
}
