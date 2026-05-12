package com.ssafy.heygent.domain.bridge.dto;

import jakarta.validation.constraints.NotBlank;

public record BridgeUnpairRequest(
    @NotBlank
    String bridgeToken
) {
}
