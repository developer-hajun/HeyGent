package com.ssafy.heygent.domain.notion.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.notion.dto.request.NotionExecuteRequest;
import com.ssafy.heygent.domain.notion.dto.response.NotionExecuteCommandResponse;
import com.ssafy.heygent.domain.notion.service.NotionApiService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/notion")
public class AiInternalNotionController {

    private final NotionApiService notionApiService;

    // AI 서버 연결을 위한 수정 본 : AI 서버는 사용자 JWT를 영속 보관하지 않으므로,
    // 내부 인증 토큰과 userId로 기존 Notion 프록시 실행 로직을 재사용합니다.
    @Operation(summary = "AI 내부 Notion 명령 배치 실행", description = "AI 서버가 내부 인증 토큰과 userId로 Notion 프록시 명령을 실행합니다.")
    @PostMapping("/execute")
    public ApiResponse<List<NotionExecuteCommandResponse>> execute(
        @Valid @RequestBody NotionExecuteRequest request
    ) {
        return ApiResponse.success(notionApiService.executeBatch(
            request.getUserId(),
            request.getUserId(),
            request.getCommands()
        ));
    }
}
