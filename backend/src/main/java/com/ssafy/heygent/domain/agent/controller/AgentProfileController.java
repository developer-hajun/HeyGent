package com.ssafy.heygent.domain.agent.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.agent.dto.request.CreateAgentProfileRequest;
import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.service.AgentProfileService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/agent-profiles")
public class AgentProfileController {

    private final AgentProfileService agentProfileService;

    @Operation(summary = "Agent Profile 생성", description = "로그인된 사용자 기준으로 AI 실행에 사용할 agent profile을 생성합니다.")
    @PostMapping
    public ApiResponse<AgentProfileResponse> createAgentProfile(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateAgentProfileRequest request
    ) {
        return ApiResponse.success(agentProfileService.create(resolveUserId(user), request));
    }

    @Operation(summary = "내 Agent Profile 목록 조회", description = "로그인된 사용자가 접근 가능한 agent profile 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<AgentProfileResponse>> getMyAgentProfiles(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(agentProfileService.getMyAgentProfiles(resolveUserId(user)));
    }

    @Operation(summary = "Agent Profile 단건 조회", description = "로그인된 사용자가 접근 가능한 agent profile을 조회합니다.")
    @GetMapping("/{agentProfileId}")
    public ApiResponse<AgentProfileResponse> getAgentProfile(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long agentProfileId
    ) {
        return ApiResponse.success(agentProfileService.getAgentProfile(resolveUserId(user), agentProfileId));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
