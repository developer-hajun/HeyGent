package com.ssafy.heygent.domain.integration.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.request.UpdateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationCredentialResponse;
import com.ssafy.heygent.domain.integration.service.IntegrationCredentialService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/integrations/{integrationId}/credentials")
public class IntegrationCredentialController {

    private final IntegrationCredentialService integrationCredentialService;

    @Operation(summary = "Integration Credential 생성", description = "외부 연동 대상에 credential을 등록합니다.")
    @PostMapping
    public ApiResponse<IntegrationCredentialResponse> createCredential(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long integrationId,
        @Valid @RequestBody CreateIntegrationCredentialRequest request
    ) {
        return ApiResponse.success(integrationCredentialService.create(resolveUserId(user), integrationId, request));
    }

    @Operation(summary = "Integration Credential 목록 조회", description = "외부 연동 대상의 credential 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<IntegrationCredentialResponse>> getCredentials(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long integrationId
    ) {
        return ApiResponse.success(integrationCredentialService.getCredentials(resolveUserId(user), integrationId));
    }

    @Operation(summary = "Integration Credential 수정", description = "외부 연동 대상의 credential secret 값을 교체합니다.")
    @PutMapping("/{credentialId}")
    public ApiResponse<IntegrationCredentialResponse> updateCredential(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long integrationId,
        @PathVariable Long credentialId,
        @Valid @RequestBody UpdateIntegrationCredentialRequest request
    ) {
        return ApiResponse.success(integrationCredentialService.update(
            resolveUserId(user),
            integrationId,
            credentialId,
            request
        ));
    }

    @Operation(summary = "Integration Credential 삭제", description = "외부 연동 대상의 credential을 삭제 처리합니다.")
    @DeleteMapping("/{credentialId}")
    public ApiResponse<Void> deleteCredential(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long integrationId,
        @PathVariable Long credentialId
    ) {
        integrationCredentialService.delete(resolveUserId(user), integrationId, credentialId);
        return ApiResponse.success();
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
