package com.ssafy.heygent.domain.iot.dto;

public record DisplayPairingStartResponse(
    String pairCode,
    long expiresInSeconds
) {
}
