package com.ssafy.heygent.domain.iot.controller;

import com.ssafy.heygent.domain.iot.dto.DisplayPairingStartRequest;
import com.ssafy.heygent.domain.iot.dto.DisplayPairingStartResponse;
import com.ssafy.heygent.domain.iot.service.DevicePairingService;
import com.ssafy.heygent.global.exception.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "IoT Pairing", description = "IoT 디스플레이 pairing API")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/iot/pairing")
public class PairingController {

    private final DevicePairingService devicePairingService;

    @Operation(summary = "IoT 디바이스 pairing code 발급")
    @PostMapping("/start")
    public ApiResponse<DisplayPairingStartResponse> start(
        @Valid @RequestBody DisplayPairingStartRequest request
    ) {
        return ApiResponse.success(devicePairingService.start(request));
    }
}
