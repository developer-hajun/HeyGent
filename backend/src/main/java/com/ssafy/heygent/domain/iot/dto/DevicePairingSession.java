package com.ssafy.heygent.domain.iot.dto;

import java.time.LocalDateTime;

public record DevicePairingSession(
    String deviceId,
    String nonce,
    String firmwareVersion,
    DevicePairingStatus status,
    LocalDateTime createdAt,
    LocalDateTime expiresAt
) {

    public static DevicePairingSession pending(
        String deviceId,
        String nonce,
        String firmwareVersion,
        LocalDateTime createdAt,
        LocalDateTime expiresAt
    ) {
        return new DevicePairingSession(
            deviceId,
            nonce,
            firmwareVersion,
            DevicePairingStatus.PENDING,
            createdAt,
            expiresAt
        );
    }
}
