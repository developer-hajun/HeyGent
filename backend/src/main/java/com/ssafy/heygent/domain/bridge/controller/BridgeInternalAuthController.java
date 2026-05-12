package com.ssafy.heygent.domain.bridge.controller;

import com.ssafy.heygent.domain.bridge.dto.BridgeInternalAuthValidateRequest;
import com.ssafy.heygent.domain.bridge.dto.BridgeInternalAuthValidateResponse;
import com.ssafy.heygent.domain.bridge.service.BridgeService;
import com.ssafy.heygent.global.exception.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Bridge Internal", description = "AI 서버가 호출하는 브릿지 토큰 검증 API. ai.internal.token 으로 보호.")
@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/bridge/auth")
public class BridgeInternalAuthController {

    private final BridgeService bridgeService;

    @Operation(summary = "브릿지 토큰 검증", description = "브릿지 hello 메시지의 토큰을 검증해 user/device 식별 정보를 반환합니다.")
    @PostMapping("/validate")
    public ApiResponse<BridgeInternalAuthValidateResponse> validate(
        @Valid @RequestBody BridgeInternalAuthValidateRequest request
    ) {
        return ApiResponse.success(bridgeService.validateBridgeToken(request.bridgeToken()));
    }
}
