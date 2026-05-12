package com.ssafy.heygent.domain.bridge.controller;

import com.ssafy.heygent.domain.bridge.dto.BridgePairRequest;
import com.ssafy.heygent.domain.bridge.dto.BridgePairResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgeUnpairRequest;
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

@Tag(name = "Bridge Pair", description = "브릿지 PC 에서 직접 호출하는 페어링 교환 API (무인증, 페어링 코드로 본인 확인)")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/bridge")
public class BridgePairController {

    private final BridgeService bridgeService;

    @Operation(summary = "페어링 코드 + 디바이스 이름으로 브릿지 토큰 교환")
    @PostMapping("/pair")
    public ApiResponse<BridgePairResponse> pair(@Valid @RequestBody BridgePairRequest request) {
        return ApiResponse.success(bridgeService.pair(request));
    }

    @Operation(summary = "브릿지 토큰으로 자기 디바이스 해제", description = "트레이 메뉴 '페어링 해제' 가 호출. 토큰 본인만 자기 디바이스를 폐기할 수 있다.")
    @PostMapping("/unpair")
    public ApiResponse<Void> unpair(@Valid @RequestBody BridgeUnpairRequest request) {
        bridgeService.unpairByToken(request.bridgeToken());
        return ApiResponse.success();
    }
}
