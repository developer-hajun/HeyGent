package com.ssafy.heygent.domain.notion.controller;

import java.util.Map;

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

    @Operation(summary = "Notion 명령 실행", description = "Notion API를 직접 호출하여 명령을 실행합니다.")
    @PostMapping("/execute")
    public ApiResponse<Map> execute(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody NotionExecuteRequest request
    ) {
        Long userId = resolveUserId(user);
        Map result = switch (request.getAction()) {
            case "create_page"       -> notionApiService.createPage(userId, request.getParams());
            case "get_page"          -> notionApiService.getPage(userId, request.getTargetId());
            case "get_page_blocks"   -> notionApiService.getPageBlocks(userId, request.getTargetId());
            case "update_page"       -> notionApiService.updatePage(userId, request.getTargetId(), request.getParams());
            case "append_blocks"     -> notionApiService.appendBlocks(userId, request.getTargetId(), request.getParams());
            case "query_database"    -> notionApiService.queryDatabase(userId, request.getTargetId(), request.getParams());
            case "insert_row"        -> notionApiService.insertDatabaseRow(userId, request.getParams());
            case "search"            -> notionApiService.search(userId, request.getParams());
            default -> throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        };
        return ApiResponse.success(result);
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
