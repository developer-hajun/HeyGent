package com.ssafy.heygent.domain.mattermost.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.mattermost.dto.AiMattermostMessageRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostMessageResponse;
import com.ssafy.heygent.domain.mattermost.service.MattermostService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/mattermost")
public class MattermostInternalController {

    private final MattermostService mattermostService;

    @Operation(summary = "AI 내부 Mattermost 메시지 전송", description = "AI 서버가 내부 인증 토큰과 userId로 Mattermost 채널 별칭에 메시지를 전송합니다.")
    @PostMapping("/messages")
    public ApiResponse<MattermostMessageResponse> sendMessage(
            @Valid @RequestBody AiMattermostMessageRequest request
    ) {
        return ApiResponse.success(mattermostService.sendMessage(request.getUserId(), request.toMessageRequest()));
    }
}
