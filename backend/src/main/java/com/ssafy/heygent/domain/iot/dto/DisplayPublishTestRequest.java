package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record DisplayPublishTestRequest(
    DisplayEventType type,
    DisplayIcon icon,
    @NotBlank String sessionId,
    @NotBlank String stepRunId,
    @Size(max = 100) String text
) {
}
