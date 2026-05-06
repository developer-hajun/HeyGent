package com.ssafy.heygent.domain.iot.dto;

import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.entity.IotDeviceStatus;

import java.time.LocalDateTime;

public record DeviceResponse(
    Long id,
    String deviceId,
    String displayName,
    IotDeviceStatus status,
    LocalDateTime lastSeenAt,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {

    public static DeviceResponse from(IotDevice device) {
        return new DeviceResponse(
            device.getId(),
            device.getDeviceId(),
            device.getDisplayName(),
            device.getStatus(),
            device.getLastSeenAt(),
            device.getCreatedAt(),
            device.getUpdatedAt()
        );
    }
}
