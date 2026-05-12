package com.ssafy.heygent.domain.bridge.dto;

import java.time.Instant;

public record BridgePairingCodeResponse(
    String code,
    Instant expiresAt
) {
}
