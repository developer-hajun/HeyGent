package com.ssafy.heygent.domain.ai.controller;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiApiKeyUpsertRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiProviderModelListResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiApiKeyConnectionResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiProviderStatusResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiApiKeyService;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiProviderStatusService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/providers")
public class AiProviderController {

    private final OpenAiApiKeyService openAiApiKeyService;
    private final OpenAiProviderStatusService openAiProviderStatusService;

    @Operation(summary = "AI provider 상태 조회", description = "로그인된 사용자의 AI provider별 연결 상태를 조회합니다.")
    @GetMapping
    public ApiResponse<OpenAiProviderStatusResponse> providers(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiProviderStatusService.getProviders(resolveUserId(user)));
    }

    @Operation(summary = "AI provider 모델 목록 조회", description = "provider별 사용 가능한 모델 목록을 조회합니다.")
    @GetMapping("/models")
    public ApiResponse<AiProviderModelListResponse> models() {
        return ApiResponse.success(openAiProviderStatusService.getProviderModels());
    }

    @Operation(summary = "AI provider API Key 등록", description = "provider별 사용자 API Key를 등록하거나 기존 값을 갱신합니다.")
    @PostMapping("/{providerName}/api-key")
    public ApiResponse<OpenAiApiKeyConnectionResponse> upsertApiKey(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Parameter(description = "API Key를 등록할 provider 이름입니다. 예: openai_api_key, gemini_api_key, claude_api_key")
        @PathVariable String providerName,
        @Valid @RequestBody OpenAiApiKeyUpsertRequest request
    ) {
        return ApiResponse.success(
            openAiApiKeyService.upsert(resolveUserId(user), providerName, request.getApiKey())
        );
    }

    @Operation(summary = "AI provider API Key 삭제", description = "provider별 사용자 API Key 연결 정보를 삭제합니다.")
    @DeleteMapping("/{providerName}/api-key")
    public ApiResponse<OpenAiApiKeyConnectionResponse> deleteApiKey(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Parameter(description = "API Key를 삭제할 provider 이름입니다. 예: openai_api_key, gemini_api_key, claude_api_key")
        @PathVariable String providerName
    ) {
        return ApiResponse.success(openAiApiKeyService.delete(resolveUserId(user), providerName));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
