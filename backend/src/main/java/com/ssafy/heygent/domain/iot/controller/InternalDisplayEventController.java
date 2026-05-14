package com.ssafy.heygent.domain.iot.controller;

import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.InternalDisplayEventRequest;
import com.ssafy.heygent.domain.iot.service.DeviceDisplayCoordinator;
import com.ssafy.heygent.global.exception.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/iot/display/events")
public class InternalDisplayEventController {

    private final DeviceDisplayCoordinator deviceDisplayCoordinator;

    @PostMapping
    public ApiResponse<DisplayPublishResult> publish(
        @Valid @RequestBody InternalDisplayEventRequest request
    ) {
        return ApiResponse.success(deviceDisplayCoordinator.publishInternal(request));
    }
}
