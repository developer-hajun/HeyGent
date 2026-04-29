package com.ssafy.heygent.domain.auth.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.auth.dto.request.AuthVerificationRequest;
import com.ssafy.heygent.domain.auth.dto.response.AuthVerificationResponse;
import com.ssafy.heygent.domain.auth.service.AuthVerificationService;
import com.ssafy.heygent.global.exception.ApiResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/internal/auth")
public class InternalAuthVerificationController {

    private static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    private final AuthVerificationService authVerificationService;

    @PostMapping("/verify")
    public ApiResponse<AuthVerificationResponse> verify(
        @RequestHeader(value = INTERNAL_SERVICE_TOKEN_HEADER, required = false) String internalServiceToken,
        @Valid @RequestBody AuthVerificationRequest request
    ) {
        return ApiResponse.success(authVerificationService.verify(internalServiceToken, request.getAccessToken()));
    }
}
