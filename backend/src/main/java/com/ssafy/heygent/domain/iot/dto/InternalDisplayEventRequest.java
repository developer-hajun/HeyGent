package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

public record InternalDisplayEventRequest(
    @NotNull Long userId,
    @NotNull DisplayEventType type,
    DisplayIcon icon,
    @NotBlank String sessionId,
    String taskRunId,
    String stepRunId,
    @Size(max = 100) String text,
    @Size(max = 60) String textKey,
    @PositiveOrZero Long ttlMs,
    Integer priority,
    @Size(max = 40) String renderMode,
    @Size(max = 40) String statusKind,
    Boolean focus
) {
}
