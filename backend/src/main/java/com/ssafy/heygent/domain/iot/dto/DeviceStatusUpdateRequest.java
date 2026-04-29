package com.ssafy.heygent.domain.iot.dto;

import com.ssafy.heygent.domain.iot.entity.IotDeviceStatus;
import jakarta.validation.constraints.NotNull;

public record DeviceStatusUpdateRequest(
    @NotNull IotDeviceStatus status
) {
}
