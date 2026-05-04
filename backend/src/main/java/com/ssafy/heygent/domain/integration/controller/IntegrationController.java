package com.ssafy.heygent.domain.integration.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationResponse;
import com.ssafy.heygent.domain.integration.service.IntegrationService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/integrations")
public class IntegrationController {

    private final IntegrationService integrationService;

    @Operation(summary = "Integration 생성", description = "로그인된 사용자 기준으로 외부 연동 대상을 생성합니다.")
    @PostMapping("/notion")
    public ApiResponse<IntegrationResponse> notionCreateIntegration(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateIntegrationRequest request
    ) {

        return ApiResponse.success(integrationService.create(resolveUserId(user), request));
    }

    @Operation(summary = "내 Integration 목록 조회", description = "로그인된 사용자의 외부 연동 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<IntegrationResponse>> getMyIntegrations(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(integrationService.getMyIntegrations(resolveUserId(user)));
    }

    @Operation(summary = "Integration 단건 조회", description = "로그인된 사용자가 소유한 외부 연동 대상을 조회합니다.")
    @GetMapping("/{integrationId}")
    public ApiResponse<IntegrationResponse> getIntegration(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long integrationId
    ) {
        return ApiResponse.success(integrationService.getIntegration(resolveUserId(user), integrationId));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
