package com.ssafy.heygent.domain.bridge.dto;

import com.ssafy.heygent.domain.bridge.entity.BridgeDevice;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

public record BridgeDeviceResponse(
    Long id,
    String deviceName,
    Instant createdAt,
    Instant lastSeenAt,
    Instant revokedAt
) {
    public static BridgeDeviceResponse from(BridgeDevice device) {
        return new BridgeDeviceResponse(
            device.getId(),
            device.getDeviceName(),
            toInstant(device.getCreatedAt()),
            toInstant(device.getLastSeenAt()),
            toInstant(device.getRevokedAt())
        );
    }

    private static Instant toInstant(LocalDateTime value) {
        if (value == null) {
            return null;
        }
        // BridgeService 는 LocalDateTime.now(ZoneOffset.UTC) 로 시각을 기록한다.
        // 컨테이너 TZ 와 상관없이 항상 UTC 로 해석해 응답에 'Z' 마커가 붙도록 한다.
        return value.toInstant(ZoneOffset.UTC);
    }
}
