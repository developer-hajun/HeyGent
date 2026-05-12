package com.ssafy.heygent.domain.bridge.dto;

public record BridgePairResponse(
    String bridgeToken,
    Long deviceId,
    Long userId,
    String deviceName
) {
}
