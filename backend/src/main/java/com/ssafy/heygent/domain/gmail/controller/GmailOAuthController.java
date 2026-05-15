package com.ssafy.heygent.domain.gmail.controller;

import java.util.List;

import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.gmail.dto.request.GmailExecuteRequest;
import com.ssafy.heygent.domain.gmail.dto.response.GmailConnectUrlResponse;
import com.ssafy.heygent.domain.gmail.dto.response.GmailExecuteCommandResponse;
import com.ssafy.heygent.domain.gmail.dto.response.GmailStatusResponse;
import com.ssafy.heygent.domain.gmail.service.GmailApiService;
import com.ssafy.heygent.domain.gmail.service.GmailOAuthService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/gmail")
public class GmailOAuthController {

    private final GmailOAuthService gmailOAuthService;
    private final GmailApiService gmailApiService;

    @Operation(summary = "Gmail 연결 URL 조회", description = "Composio를 통한 Gmail OAuth 연결 URL을 반환합니다.")
    @GetMapping("/connect-url")
    public ApiResponse<GmailConnectUrlResponse> getConnectUrl(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(gmailOAuthService.getConnectUrl(resolveUserId(user)));
    }

    @Operation(summary = "Gmail 연결 상태 조회", description = "현재 사용자의 Gmail 연결 상태를 반환합니다.")
    @GetMapping("/status")
    public ApiResponse<GmailStatusResponse> getStatus(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(gmailOAuthService.getStatus(resolveUserId(user)));
    }

    @Operation(summary = "Gmail 연결 해제", description = "현재 사용자의 Gmail 연결을 해제합니다.")
    @DeleteMapping("/disconnect")
    public ApiResponse<Void> disconnect(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        gmailOAuthService.disconnect(resolveUserId(user));
        return ApiResponse.success();
    }

    @Operation(summary = "Gmail 명령 배치 실행", description = "여러 Gmail API 프록시 명령을 순서대로 실행하고 각 결과를 반환합니다.")
    @PostMapping("/execute")
    public ApiResponse<List<GmailExecuteCommandResponse>> execute(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody GmailExecuteRequest request
    ) {
        return ApiResponse.success(gmailApiService.executeBatch(
            resolveUserId(user),
            request.getUserId(),
            request.getCommands()
        ));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
