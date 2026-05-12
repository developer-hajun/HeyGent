package com.ssafy.heygent.domain.bridge.dto;

public record BridgeInternalAuthValidateResponse(
    Long userId,
    Long deviceId,
    String deviceName
) {
}
