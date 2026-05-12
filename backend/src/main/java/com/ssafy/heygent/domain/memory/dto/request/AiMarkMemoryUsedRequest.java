package com.ssafy.heygent.domain.memory.dto.request;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class AiMarkMemoryUsedRequest {

    @NotNull(message = "사용자 ID는 필수입니다.")
    private Long userId;

    @DecimalMin(value = "0.0", message = "유용도는 0.0 이상이어야 합니다.")
    @DecimalMax(value = "1.0", message = "유용도는 1.0 이하여야 합니다.")
    private Double usefulnessScore;

    @Size(max = 100, message = "TaskRun ID는 100자 이하여야 합니다.")
    private String sourceTaskRunId;
}
