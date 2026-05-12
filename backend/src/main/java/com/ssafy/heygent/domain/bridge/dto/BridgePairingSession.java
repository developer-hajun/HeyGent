package com.ssafy.heygent.domain.bridge.dto;

import java.time.Instant;

public record BridgePairingSession(
    String code,
    Long userId,
    Instant createdAt,
    Instant expiresAt
) {
}
