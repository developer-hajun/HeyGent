package com.ssafy.heygent.domain.iot.controller;

import com.ssafy.heygent.domain.iot.dto.DevicePairRequest;
import com.ssafy.heygent.domain.iot.dto.DeviceRegisterRequest;
import com.ssafy.heygent.domain.iot.dto.DeviceResponse;
import com.ssafy.heygent.domain.iot.dto.DeviceStatusUpdateRequest;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishTestRequest;
import com.ssafy.heygent.domain.iot.service.DevicePairingService;
import com.ssafy.heygent.domain.iot.service.DeviceService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@Tag(name = "IoT Device", description = "IoT 디스플레이 디바이스 관리 API")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/iot/devices")
public class DeviceController {

    private final DeviceService deviceService;
    private final DevicePairingService devicePairingService;

    @Operation(summary = "IoT 디바이스 등록")
    @PostMapping
    public ApiResponse<DeviceResponse> register(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @Valid @RequestBody DeviceRegisterRequest request
    ) {
        return ApiResponse.success(deviceService.register(principal.getUserId(), request));
    }

    @Operation(summary = "내 IoT 디바이스 목록 조회")
    @GetMapping
    public ApiResponse<List<DeviceResponse>> list(
        @AuthenticationPrincipal CustomUserPrincipal principal
    ) {
        return ApiResponse.success(deviceService.list(principal.getUserId()));
    }

    @Operation(summary = "IoT 디바이스 pairing code 등록")
    @PostMapping("/pair")
    public ApiResponse<DeviceResponse> pair(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @Valid @RequestBody DevicePairRequest request
    ) {
        return ApiResponse.success(devicePairingService.pair(principal.getUserId(), request));
    }

    @Operation(summary = "IoT 디바이스 상태 변경")
    @PatchMapping("/{deviceId}/status")
    public ApiResponse<DeviceResponse> updateStatus(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @PathVariable String deviceId,
        @Valid @RequestBody DeviceStatusUpdateRequest request
    ) {
        return ApiResponse.success(deviceService.updateStatus(principal.getUserId(), deviceId, request.status()));
    }

    @Operation(summary = "IoT 디바이스 해제")
    @DeleteMapping("/{deviceId}")
    public ApiResponse<Void> unpair(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @PathVariable String deviceId
    ) {
        deviceService.unpair(principal.getUserId(), deviceId);
        return ApiResponse.success();
    }

    @Operation(summary = "IoT 디스플레이 테스트 메시지 발행")
    @PostMapping("/{deviceId}/display/test")
    public ApiResponse<DisplayPublishResult> publishDisplayTest(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @PathVariable String deviceId,
        @Valid @RequestBody DisplayPublishTestRequest request
    ) {
        return ApiResponse.success(deviceService.publishTest(principal.getUserId(), deviceId, request));
    }
}
