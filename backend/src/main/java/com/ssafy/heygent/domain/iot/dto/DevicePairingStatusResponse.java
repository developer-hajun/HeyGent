package com.ssafy.heygent.domain.iot.dto;

public record DevicePairingStatusResponse(
    String deviceId,
    boolean paired,
    String status
) {

    public static DevicePairingStatusResponse unpaired(String deviceId) {
        return new DevicePairingStatusResponse(deviceId, false, "UNPAIRED");
    }

    public static DevicePairingStatusResponse paired(String deviceId, String status) {
        return new DevicePairingStatusResponse(deviceId, true, status);
    }
}
