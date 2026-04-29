package com.ssafy.heygent.domain.workspace.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.workspace.dto.request.CreateWorkspaceRequest;
import com.ssafy.heygent.domain.workspace.dto.response.WorkspaceResponse;
import com.ssafy.heygent.domain.workspace.service.WorkspaceService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/workspaces")
public class WorkspaceController {

    private final WorkspaceService workspaceService;

    @Operation(summary = "워크스페이스 생성", description = "로그인된 사용자 기준으로 AI 작업에서 사용할 workspace를 생성합니다.")
    @PostMapping
    public ApiResponse<WorkspaceResponse> createWorkspace(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateWorkspaceRequest request
    ) {
        return ApiResponse.success(workspaceService.create(resolveUserId(user), request));
    }

    @Operation(summary = "내 워크스페이스 목록 조회", description = "로그인된 사용자가 접근 가능한 workspace 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<WorkspaceResponse>> getMyWorkspaces(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(workspaceService.getMyWorkspaces(resolveUserId(user)));
    }

    @Operation(summary = "워크스페이스 단건 조회", description = "로그인된 사용자가 접근 가능한 workspace를 조회합니다.")
    @GetMapping("/{workspaceKey}")
    public ApiResponse<WorkspaceResponse> getWorkspace(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable String workspaceKey
    ) {
        return ApiResponse.success(workspaceService.getWorkspace(resolveUserId(user), workspaceKey));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
