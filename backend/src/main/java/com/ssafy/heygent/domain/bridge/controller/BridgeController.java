package com.ssafy.heygent.domain.bridge.controller;

import com.ssafy.heygent.domain.bridge.dto.BridgeDeviceResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgePairingCodeResponse;
import com.ssafy.heygent.domain.bridge.service.BridgeService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@Tag(name = "Bridge", description = "사용자 PC 브릿지 페어링/디바이스 관리 API")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/bridge")
public class BridgeController {

    private final BridgeService bridgeService;

    @Operation(summary = "브릿지 페어링 코드 발급", description = "현재 로그인된 사용자가 자신의 PC 브릿지를 연결할 6자리 코드를 발급받습니다. TTL 5분.")
    @PostMapping("/pairing")
    public ApiResponse<BridgePairingCodeResponse> issuePairingCode(
        @AuthenticationPrincipal CustomUserPrincipal principal
    ) {
        return ApiResponse.success(bridgeService.issuePairingCode(principal.getUserId()));
    }

    @Operation(summary = "내 브릿지 디바이스 목록")
    @GetMapping("/devices")
    public ApiResponse<List<BridgeDeviceResponse>> listDevices(
        @AuthenticationPrincipal CustomUserPrincipal principal
    ) {
        return ApiResponse.success(bridgeService.listDevices(principal.getUserId()));
    }

    @Operation(
        summary = "브릿지 디바이스 해제/삭제",
        description = "활성 디바이스면 토큰을 폐기(revoke)하고, 이미 폐기된 디바이스면 row 자체를 삭제한다."
    )
    @DeleteMapping("/devices/{deviceId}")
    public ApiResponse<Void> revokeDevice(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @PathVariable Long deviceId
    ) {
        bridgeService.revokeDevice(principal.getUserId(), deviceId);
        return ApiResponse.success();
    }
}
