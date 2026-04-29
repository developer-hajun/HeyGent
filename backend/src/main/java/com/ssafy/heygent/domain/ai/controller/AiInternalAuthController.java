package com.ssafy.heygent.domain.ai.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.AiAuthValidateRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiAuthValidateResponse;
import com.ssafy.heygent.domain.ai.service.AiInternalAuthService;
import com.ssafy.heygent.global.exception.ApiResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/auth")
public class AiInternalAuthController {

    private final AiInternalAuthService aiInternalAuthService;

    @PostMapping("/validate")
    public ApiResponse<AiAuthValidateResponse> validate(
        @Valid @RequestBody AiAuthValidateRequest request
    ) {
        return ApiResponse.success(aiInternalAuthService.validate(request));
    }
}
