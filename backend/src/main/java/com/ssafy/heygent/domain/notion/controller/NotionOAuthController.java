package com.ssafy.heygent.domain.notion.controller;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.notion.dto.response.NotionConnectUrlResponse;
import com.ssafy.heygent.domain.notion.dto.response.NotionStatusResponse;
import com.ssafy.heygent.domain.notion.service.NotionOAuthService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/notion")
public class NotionOAuthController {

    private final NotionOAuthService notionOAuthService;

    @Operation(summary = "Notion 연결 URL 조회", description = "Composio를 통한 Notion OAuth 연결 URL을 반환합니다.")
    @GetMapping("/connect-url")
    public ApiResponse<NotionConnectUrlResponse> getConnectUrl(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(notionOAuthService.getConnectUrl(resolveUserId(user)));
    }

    @Operation(summary = "Notion 연결 상태 조회", description = "현재 사용자의 Notion 연결 상태를 반환합니다.")
    @GetMapping("/status")
    public ApiResponse<NotionStatusResponse> getStatus(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(notionOAuthService.getStatus(resolveUserId(user)));
    }

    @Operation(summary = "Notion 연결 해제", description = "현재 사용자의 Notion 연결을 해제합니다.")
    @DeleteMapping("/disconnect")
    public ApiResponse<Void> disconnect(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        notionOAuthService.disconnect(resolveUserId(user));
        return ApiResponse.success();
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
