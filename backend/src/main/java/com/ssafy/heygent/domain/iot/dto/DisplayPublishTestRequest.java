package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.Size;

public record DisplayPublishTestRequest(
    DisplayEventType type,
    String taskRunId,
    @Size(max = 100) String text
) {
}
