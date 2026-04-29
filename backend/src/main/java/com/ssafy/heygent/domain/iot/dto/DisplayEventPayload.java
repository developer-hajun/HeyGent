package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

public record DisplayEventPayload(
    @NotNull DisplayEventType type,
    @NotBlank String sessionId,
    @NotBlank String stepRunId,
    @NotNull DisplayIcon icon,
    @NotBlank String text,
    @PositiveOrZero long ttlMs,
    long seq
) {
}
