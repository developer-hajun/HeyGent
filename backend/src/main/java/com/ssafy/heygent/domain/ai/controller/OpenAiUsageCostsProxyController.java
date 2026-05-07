package com.ssafy.heygent.domain.ai.controller;

import java.time.LocalDate;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageCostsProxyResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiUsageCostsProxyService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/openai/usages")
public class OpenAiUsageCostsProxyController {

    private final OpenAiUsageCostsProxyService openAiUsageCostsProxyService;

    @Operation(summary = "내 OpenAI usage 비용 조회", description = "로그인된 사용자의 provider별 OpenAI usage 비용을 기간 조건으로 조회합니다.")
    @GetMapping("/me")
    public ApiResponse<OpenAiUsageCostsProxyResponse> getMyOpenAiUsage(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @RequestParam String providerName,
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
        @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to
    ) {
        return ApiResponse.success(
            openAiUsageCostsProxyService.getUsage(resolveUserId(user), providerName, from, to)
        );
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
