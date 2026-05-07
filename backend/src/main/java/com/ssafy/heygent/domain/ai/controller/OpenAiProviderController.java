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

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/openai")
public class OpenAiProviderController {

    private final OpenAiProviderStatusService openAiProviderStatusService;

    @Operation(summary = "OpenAI 모델 목록 조회", description = "서비스에서 사용할 수 있는 OpenAI 모델 목록을 조회합니다.")
    @GetMapping("/models")
    public ApiResponse<OpenAiModelListResponse> models() {
        return ApiResponse.success(openAiProviderStatusService.getModels());
    }

    @Operation(summary = "OpenAI provider 상태 조회", description = "로그인된 사용자의 OpenAI 연결 방식과 provider 사용 가능 상태를 조회합니다.")
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
