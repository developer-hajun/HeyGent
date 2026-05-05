package com.ssafy.heygent.domain.ai.controller;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiModelListResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiProviderStatusResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiProviderStatusService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/openai")
public class OpenAiProviderController {

    private final OpenAiProviderStatusService openAiProviderStatusService;

    @GetMapping("/models")
    public ApiResponse<OpenAiModelListResponse> models() {
        return ApiResponse.success(openAiProviderStatusService.getModels());
    }

    @GetMapping("/providers")
    public ApiResponse<OpenAiProviderStatusResponse> providers(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiProviderStatusService.getProviders(resolveUserId(user)));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
