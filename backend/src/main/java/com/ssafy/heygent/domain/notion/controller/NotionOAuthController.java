package com.ssafy.heygent.domain.notion.controller;

import java.util.List;

import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.notion.dto.request.NotionExecuteRequest;
import com.ssafy.heygent.domain.notion.dto.response.NotionConnectUrlResponse;
import com.ssafy.heygent.domain.notion.dto.response.NotionExecuteCommandResponse;
import com.ssafy.heygent.domain.notion.dto.response.NotionStatusResponse;
import com.ssafy.heygent.domain.notion.service.NotionApiService;
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
    private final NotionApiService notionApiService;

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

    @Operation(summary = "Notion 명령 배치 실행", description = "여러 Notion API 프록시 명령을 순서대로 실행하고 각 결과를 반환합니다.")
    @PostMapping("/execute")
    public ApiResponse<List<NotionExecuteCommandResponse>> execute(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody NotionExecuteRequest request
    ) {
        return ApiResponse.success(notionApiService.executeBatch(
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
