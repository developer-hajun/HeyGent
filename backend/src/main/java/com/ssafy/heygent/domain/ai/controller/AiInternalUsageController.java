package com.ssafy.heygent.domain.ai.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.AiCommandUsageRecordRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiCommandUsageRecordResponse;
import com.ssafy.heygent.domain.ai.openai.service.AiCommandUsageService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/usages")
public class AiInternalUsageController {

    private final AiCommandUsageService aiCommandUsageService;

    @Operation(summary = "AI 내부 명령 사용량 기록", description = "AI 서버가 모델 호출 1회에 대한 토큰 사용량과 예상 비용을 기록합니다.")
    @PostMapping("/commands")
    public ApiResponse<AiCommandUsageRecordResponse> recordCommandUsage(
        @Valid @RequestBody AiCommandUsageRecordRequest request
    ) {
        return ApiResponse.success(aiCommandUsageService.record(request));
    }
}
