package com.ssafy.heygent.domain.ai.controller;

import java.time.LocalDate;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageListResponse;
import com.ssafy.heygent.domain.ai.openai.service.AiCommandUsageService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/usages")
public class AiUsageController {

    private final AiCommandUsageService aiCommandUsageService;

    @Operation(summary = "내 AI 명령 사용량 조회", description = "로그인된 사용자의 명령별 토큰 사용량과 예상 비용 기록을 조회합니다.")
    @GetMapping("/me/commands")
    public ApiResponse<AiCommandUsageListResponse> getMyCommandUsages(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
        @RequestParam(required = false) String taskRunId,
        @RequestParam(required = false) String sessionId,
        @RequestParam(required = false) Integer limit
    ) {
        return ApiResponse.success(aiCommandUsageService.getMyUsages(
            resolveUserId(user),
            from,
            to,
            taskRunId,
            sessionId,
            limit
        ));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
