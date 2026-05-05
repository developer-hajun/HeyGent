package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record DisplayPairingStartRequest(
    @NotBlank @Size(max = 80) String deviceId,
    @Size(max = 100) String nonce,
    @Size(max = 50) String firmwareVersion
) {
}
