package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

public record DisplayEventPayload(
    @NotNull DisplayEventType type,
    @NotBlank String sessionId,
    String taskRunId,
    String stepRunId,
    @NotNull DisplayIcon icon,
    @NotBlank String text,
    String textKey,
    @PositiveOrZero long ttlMs,
    int priority,
    String renderMode,
    String statusKind,
    boolean focus,
    long seq
) {

    public DisplayEventPayload(
        DisplayEventType type,
        String sessionId,
        String stepRunId,
        DisplayIcon icon,
        String text,
        long ttlMs,
        long seq
    ) {
        this(type, sessionId, null, stepRunId, icon, text, null, ttlMs, 0, "AUTO", null, false, seq);
    }
}
