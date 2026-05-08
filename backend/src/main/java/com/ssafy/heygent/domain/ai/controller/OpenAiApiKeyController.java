package com.ssafy.heygent.domain.ai.controller;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiApiKeyUpsertRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiApiKeyConnectionResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiApiKeyService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/openai/api-key")
public class OpenAiApiKeyController {

    private final OpenAiApiKeyService openAiApiKeyService;

    @Operation(summary = "OpenAI API Key 등록", description = "로그인된 사용자의 OpenAI API Key를 등록하거나 기존 값을 갱신합니다.")
    @PostMapping
    public ApiResponse<OpenAiApiKeyConnectionResponse> upsert(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody OpenAiApiKeyUpsertRequest request
    ) {
        return ApiResponse.success(openAiApiKeyService.upsert(resolveUserId(user), request.getApiKey()));
    }

    @Operation(summary = "OpenAI API Key 삭제", description = "로그인된 사용자의 OpenAI API Key 연결 정보를 삭제합니다.")
    @DeleteMapping
    public ApiResponse<OpenAiApiKeyConnectionResponse> delete(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiApiKeyService.delete(resolveUserId(user)));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
