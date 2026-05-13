package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record DeviceInteractionRequest(
    @NotNull DeviceInteractionType interactionType,
    @Size(max = 100) String currentTaskRunId
) {
}
