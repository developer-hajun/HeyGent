package com.ssafy.heygent.domain.iot.controller;

import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.StepRunDisplayPublishRequest;
import com.ssafy.heygent.domain.iot.service.DisplayEventPublishService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "IoT Display Event", description = "IoT 디스플레이 이벤트 발행 API")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/iot/display/events")
public class DisplayEventController {

    private final DisplayEventPublishService displayEventPublishService;

    @Operation(summary = "StepRun 기반 IoT 디스플레이 이벤트 발행")
    @PostMapping
    public ApiResponse<DisplayPublishResult> publishStepRunEvent(
        @AuthenticationPrincipal CustomUserPrincipal principal,
        @Valid @RequestBody StepRunDisplayPublishRequest request
    ) {
        return ApiResponse.success(displayEventPublishService.publish(
            principal.getUserId(),
            request.type(),
            request.icon(),
            request.sessionId(),
            request.stepRunId(),
            request.text()
        ));
    }
}
