package com.ssafy.heygent.domain.gmail.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.gmail.dto.request.GmailExecuteRequest;
import com.ssafy.heygent.domain.gmail.dto.response.GmailExecuteCommandResponse;
import com.ssafy.heygent.domain.gmail.service.GmailApiService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/gmail")
public class AiInternalGmailController {

    private final GmailApiService gmailApiService;

    // AI 서버 연결을 위한 임시 본 : AI 서버는 사용자 JWT를 직접 보관하지 않으므로,
    // 내부 인증 토큰과 userId로 기존 Gmail 프록시 실행 로직을 재사용합니다.
    @Operation(summary = "AI 내부 Gmail 명령 배치 실행", description = "AI 서버가 내부 인증 토큰과 userId로 Gmail 프록시 명령을 실행합니다.")
    @PostMapping("/execute")
    public ApiResponse<List<GmailExecuteCommandResponse>> execute(
        @Valid @RequestBody GmailExecuteRequest request
    ) {
        return ApiResponse.success(gmailApiService.executeBatch(
            request.getUserId(),
            request.getUserId(),
            request.getCommands()
        ));
    }
}
