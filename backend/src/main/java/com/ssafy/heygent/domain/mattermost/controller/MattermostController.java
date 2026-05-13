package com.ssafy.heygent.domain.mattermost.controller;

import java.util.List;

import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.mattermost.dto.MattermostChannelCreateRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostChannelResponse;
import com.ssafy.heygent.domain.mattermost.dto.MattermostChannelUpdateRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostMessageRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostMessageResponse;
import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookResponse;
import com.ssafy.heygent.domain.mattermost.service.MattermostService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;

@Tag(name = "Mattermost", description = "Mattermost 채널 설정 및 메시지 전송 API")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/mattermost")
public class MattermostController {

    private final MattermostService mattermostService;

    @Operation(summary = "내 Mattermost 채널 목록 조회")
    @GetMapping("/channels")
    public ApiResponse<List<MattermostChannelResponse>> listChannels(
            @AuthenticationPrincipal CustomUserPrincipal principal
    ) {
        return ApiResponse.success(mattermostService.listChannels(principal.getUserId()));
    }

    @Operation(summary = "Mattermost 채널 설정 추가", description = "채널 별칭과 Incoming Webhook URL을 저장합니다.")
    @PostMapping("/channels")
    public ApiResponse<MattermostChannelResponse> createChannel(
            @AuthenticationPrincipal CustomUserPrincipal principal,
            @Valid @RequestBody MattermostChannelCreateRequest request
    ) {
        return ApiResponse.success(mattermostService.createChannel(principal.getUserId(), request));
    }

    @Operation(summary = "Mattermost 채널 설정 수정", description = "Webhook URL은 값이 있을 때만 교체합니다.")
    @PutMapping("/channels/{channelId}")
    public ApiResponse<MattermostChannelResponse> updateChannel(
            @AuthenticationPrincipal CustomUserPrincipal principal,
            @PathVariable Long channelId,
            @Valid @RequestBody MattermostChannelUpdateRequest request
    ) {
        return ApiResponse.success(mattermostService.updateChannel(principal.getUserId(), channelId, request));
    }

    @Operation(summary = "Mattermost 기본 채널 지정")
    @PostMapping("/channels/{channelId}/default")
    public ApiResponse<MattermostChannelResponse> setDefaultChannel(
            @AuthenticationPrincipal CustomUserPrincipal principal,
            @PathVariable Long channelId
    ) {
        return ApiResponse.success(mattermostService.setDefaultChannel(principal.getUserId(), channelId));
    }

    @Operation(summary = "Mattermost 채널 설정 삭제")
    @DeleteMapping("/channels/{channelId}")
    public ApiResponse<Void> deleteChannel(
            @AuthenticationPrincipal CustomUserPrincipal principal,
            @PathVariable Long channelId
    ) {
        mattermostService.deleteChannel(principal.getUserId(), channelId);
        return ApiResponse.success();
    }

    @Operation(summary = "Mattermost 별칭 기반 메시지 전송", description = "target이 없으면 기본 채널로 메시지를 전송합니다.")
    @PostMapping("/messages")
    public ApiResponse<MattermostMessageResponse> sendMessage(
            @AuthenticationPrincipal CustomUserPrincipal principal,
            @Valid @RequestBody MattermostMessageRequest request
    ) {
        return ApiResponse.success(mattermostService.sendMessage(principal.getUserId(), request));
    }

    @Operation(summary = "Mattermost Webhook 메시지 전송", description = "PoC용으로 입력받은 Incoming Webhook URL로 메시지를 전송합니다.")
    @PostMapping("/webhook")
    public ApiResponse<MattermostWebhookResponse> sendWebhook(
            @Valid @RequestBody MattermostWebhookRequest request
    ) {
        return ApiResponse.success(mattermostService.sendWebhook(request));
    }
}
