package com.ssafy.heygent.domain.ai.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.AiAuthValidateRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiAuthValidateResponse;
import com.ssafy.heygent.domain.ai.service.AiInternalAuthService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/auth")
public class AiInternalAuthController {

    private final AiInternalAuthService aiInternalAuthService;

    @Operation(summary = "AI 내부 인증 검증", description = "AI 서버가 전달한 인증 정보를 검증하고 사용자 식별 정보를 반환합니다.")
    @PostMapping("/validate")
    public ApiResponse<AiAuthValidateResponse> validate(
        @Valid @RequestBody AiAuthValidateRequest request
    ) {
        return ApiResponse.success(aiInternalAuthService.validate(request));
    }
}
