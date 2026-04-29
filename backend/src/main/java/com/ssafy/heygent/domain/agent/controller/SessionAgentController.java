package com.ssafy.heygent.domain.agent.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.service.SessionAgentService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/sessions/{sessionId}")
public class SessionAgentController {

    private final SessionAgentService sessionAgentService;

    @Operation(summary = "세션 Main Agent 연결", description = "product session에 main agent profile을 연결합니다.")
    @PutMapping("/main-agents/{agentProfileId}")
    public ApiResponse<AgentProfileResponse> connectMainAgent(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId,
        @PathVariable Long agentProfileId
    ) {
        return ApiResponse.success(sessionAgentService.connectMainAgent(
            resolveUserId(user),
            sessionId,
            agentProfileId
        ));
    }

    @Operation(summary = "세션 SubAgent 연결", description = "product session에 subagent profile을 연결합니다.")
    @PutMapping("/sub-agents/{agentProfileId}")
    public ApiResponse<AgentProfileResponse> connectSubAgent(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId,
        @PathVariable Long agentProfileId
    ) {
        return ApiResponse.success(sessionAgentService.connectSubAgent(
            resolveUserId(user),
            sessionId,
            agentProfileId
        ));
    }

    @Operation(summary = "세션 SubAgent 연결 해제", description = "product session에 연결된 subagent profile을 해제합니다.")
    @DeleteMapping("/sub-agents/{agentProfileId}")
    public ApiResponse<Void> disconnectSubAgent(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId,
        @PathVariable Long agentProfileId
    ) {
        sessionAgentService.disconnectSubAgent(resolveUserId(user), sessionId, agentProfileId);
        return ApiResponse.success();
    }

    @Operation(summary = "세션 Main Agent 조회", description = "product session에 연결된 main agent profile을 조회합니다.")
    @GetMapping("/main-agent")
    public ApiResponse<AgentProfileResponse> getMainAgent(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId
    ) {
        return ApiResponse.success(sessionAgentService.getMainAgent(resolveUserId(user), sessionId));
    }

    @Operation(summary = "세션 SubAgent 목록 조회", description = "product session에 연결된 subagent profile 목록을 조회합니다.")
    @GetMapping("/sub-agents")
    public ApiResponse<List<AgentProfileResponse>> getSubAgents(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId
    ) {
        return ApiResponse.success(sessionAgentService.getSubAgents(resolveUserId(user), sessionId));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
