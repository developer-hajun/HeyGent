package com.ssafy.heygent.domain.mattermost.controller;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookResponse;
import com.ssafy.heygent.domain.mattermost.service.MattermostService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/mattermost")
public class MattermostController {

    private final MattermostService mattermostService;

    @Operation(summary = "Mattermost Webhook 메시지 전송", description = "PoC용으로 입력받은 Incoming Webhook URL로 메시지를 전송합니다.")
    @PostMapping("/webhook")
    public ApiResponse<MattermostWebhookResponse> sendWebhook(
            @Valid @RequestBody MattermostWebhookRequest request
    ) {
        return ApiResponse.success(mattermostService.sendWebhook(request));
    }
}
