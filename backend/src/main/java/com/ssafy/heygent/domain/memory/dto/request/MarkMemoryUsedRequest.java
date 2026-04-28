package com.ssafy.heygent.domain.memory.dto.request;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import lombok.Getter;

@Getter
public class MarkMemoryUsedRequest {

    @DecimalMin(value = "0.0", message = "유용도는 0.0 이상이어야 합니다.")
    @DecimalMax(value = "1.0", message = "유용도는 1.0 이하여야 합니다.")
    private Double usefulnessScore;
}
