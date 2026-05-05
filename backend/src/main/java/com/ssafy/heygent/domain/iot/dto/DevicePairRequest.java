package com.ssafy.heygent.domain.iot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record DevicePairRequest(
    @NotBlank @Pattern(regexp = "\\d{6}") String pairCode,
    @Size(max = 100) String displayName
) {
}
