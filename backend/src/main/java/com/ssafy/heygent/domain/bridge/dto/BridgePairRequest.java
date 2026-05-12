package com.ssafy.heygent.domain.bridge.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record BridgePairRequest(
    @NotBlank
    @Pattern(regexp = "\\d{6}", message = "페어링 코드는 6자리 숫자여야 합니다.")
    String code,

    @NotBlank
    @Size(max = 60, message = "디바이스 이름은 60자 이하여야 합니다.")
    String deviceName
) {
}
