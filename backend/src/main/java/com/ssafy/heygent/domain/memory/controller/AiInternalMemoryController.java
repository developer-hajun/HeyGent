package com.ssafy.heygent.domain.memory.controller;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.memory.dto.request.AiCreateMemoryCandidatesRequest;
import com.ssafy.heygent.domain.memory.dto.request.AiMarkMemoryUsedRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.service.UserMemoryService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/memories")
public class AiInternalMemoryController {

    private final UserMemoryService userMemoryService;

    @Operation(summary = "AI 내부 장기기억 recall", description = "AI 서버가 내부 인증 토큰과 userId로 prompt 주입용 장기기억을 조회합니다.")
    @GetMapping("/recall")
    public ApiResponse<List<UserMemoryResponse>> recallMemories(
        @RequestParam Long userId,
        @RequestParam(required = false) Integer limit,
        @RequestParam(required = false) String query,
        @RequestParam(required = false) MemoryStoreType storeType,
        @RequestParam(required = false) MemoryType memoryType,
        @RequestParam(required = false) MemoryScopeType scopeType,
        @RequestParam(required = false) String workspaceKey,
        @RequestParam(required = false) String resourceId,
        @RequestParam(required = false) List<String> tags,
        @RequestParam(required = false) List<String> metadataCategories
    ) {
        return ApiResponse.success(userMemoryService.recall(
            userId,
            limit,
            query,
            storeType,
            memoryType,
            scopeType,
            workspaceKey,
            null,
            resourceId,
            tags,
            metadataCategories
        ));
    }

    @Operation(summary = "AI 내부 장기기억 후보 저장", description = "AI 서버가 내부 인증 토큰과 userId로 저장 가능한 장기기억 후보를 기록합니다.")
    @PostMapping("/candidates")
    public ApiResponse<List<UserMemoryResponse>> createMemoryCandidates(
        @Valid @RequestBody AiCreateMemoryCandidatesRequest request
    ) {
        return ApiResponse.success(userMemoryService.createCandidates(request.getUserId(), request.getCandidates()));
    }

    @Operation(summary = "AI 내부 장기기억 사용 피드백", description = "AI 서버가 내부 인증 토큰과 userId로 실제 사용한 장기기억을 기록합니다.")
    @PostMapping("/{memoryId}/used")
    public ApiResponse<UserMemoryResponse> markMemoryUsed(
        @PathVariable Long memoryId,
        @Valid @RequestBody AiMarkMemoryUsedRequest request
    ) {
        return ApiResponse.success(userMemoryService.markUsed(
            request.getUserId(),
            memoryId,
            request.getUsefulnessScore()
        ));
    }
}
