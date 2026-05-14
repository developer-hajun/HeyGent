package com.ssafy.heygent.domain.iot.dto;

public record DisplayFocusState(
    String taskRunId,
    String reason,
    long expiresAtEpochMs
) {
}
