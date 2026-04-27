package com.ssafy.heygent.domain.memory.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryCandidatesRequest;
import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.service.UserMemoryService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/memories")
public class UserMemoryController {

    private final UserMemoryService userMemoryService;

    @Operation(summary = "사용자 장기기억 저장", description = "로그인된 사용자 기준으로 장기기억 후보를 저장합니다.")
    @PostMapping
    public ApiResponse<UserMemoryResponse> createMemory(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateMemoryRequest request
    ) {
        return ApiResponse.success(userMemoryService.create(resolveUserId(user), request));
    }

    @Operation(summary = "AI 장기기억 후보 저장", description = "AI가 제안한 장기기억 후보 중 저장 가능한 항목만 저장합니다.")
    @PostMapping("/candidates")
    public ApiResponse<List<UserMemoryResponse>> createMemoryCandidates(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateMemoryCandidatesRequest request
    ) {
        return ApiResponse.success(userMemoryService.createCandidates(resolveUserId(user), request));
    }

    @Operation(summary = "내 장기기억 목록 조회", description = "로그인된 사용자의 활성 장기기억 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<UserMemoryResponse>> getMyMemories(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(userMemoryService.getMyMemories(resolveUserId(user)));
    }

    @Operation(summary = "AI recall용 장기기억 조회", description = "AI 요청 전에 prompt에 주입할 활성 장기기억을 조회합니다.")
    @GetMapping("/recall")
    public ApiResponse<List<UserMemoryResponse>> recallMemories(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @RequestParam(required = false) Integer limit,
        @RequestParam(required = false) String query,
        @RequestParam(required = false) MemoryType memoryType,
        @RequestParam(required = false) MemoryScopeType scopeType,
        @RequestParam(required = false) String workspaceKey,
        @RequestParam(required = false) String sessionKey,
        @RequestParam(required = false) String resourceId,
        @RequestParam(required = false) List<String> tags
    ) {
        return ApiResponse.success(userMemoryService.recall(
            resolveUserId(user),
            limit,
            query,
            memoryType,
            scopeType,
            workspaceKey,
            sessionKey,
            resourceId,
            tags
        ));
    }

    @Operation(summary = "장기기억 삭제", description = "로그인된 사용자의 장기기억을 논리 삭제합니다.")
    @DeleteMapping("/{memoryId}")
    public ApiResponse<Void> deleteMemory(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long memoryId
    ) {
        userMemoryService.delete(resolveUserId(user), memoryId);
        return ApiResponse.success();
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
