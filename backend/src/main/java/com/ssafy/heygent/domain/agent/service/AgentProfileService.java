package com.ssafy.heygent.domain.agent.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.agent.dto.request.CreateAgentProfileRequest;
import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileStatus;
import com.ssafy.heygent.domain.agent.repository.AgentProfileRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AgentProfileService {

    private final AgentProfileRepository agentProfileRepository;
    private final WorkspaceAccessService workspaceAccessService;

    @Transactional
    public AgentProfileResponse create(Long userId, CreateAgentProfileRequest request) {
        AgentProfile agentProfile = AgentProfile.builder()
            .ownerUserId(userId)
            .workspaceKey(resolveWorkspaceKey(userId, request.getWorkspaceKey()))
            .name(request.getName().trim())
            .type(request.getType())
            .model(trimToNull(request.getModel()))
            .systemPrompt(trimToNull(request.getSystemPrompt()))
            .status(AgentProfileStatus.ACTIVE)
            .build();

        return AgentProfileResponse.from(agentProfileRepository.save(agentProfile));
    }

    public List<AgentProfileResponse> getMyAgentProfiles(Long userId) {
        return agentProfileRepository.findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
                userId,
                AgentProfileStatus.ACTIVE
            )
            .stream()
            .map(AgentProfileResponse::from)
            .toList();
    }

    public AgentProfileResponse getAgentProfile(Long userId, Long agentProfileId) {
        return AgentProfileResponse.from(findOwnedAgentProfile(userId, agentProfileId));
    }

    public AgentProfile findOwnedAgentProfile(Long userId, Long agentProfileId) {
        if (agentProfileId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return agentProfileRepository.findByIdAndOwnerUserIdAndStatus(
                agentProfileId,
                userId,
                AgentProfileStatus.ACTIVE
            )
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }

    public void validateWorkspaceBoundary(String sessionWorkspaceKey, AgentProfile agentProfile) {
        if (!StringUtils.hasText(sessionWorkspaceKey)) {
            return;
        }
        if (!sessionWorkspaceKey.equals(agentProfile.getWorkspaceKey())) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }
    }

    private String resolveWorkspaceKey(Long userId, String workspaceKey) {
        if (!StringUtils.hasText(workspaceKey)) {
            return null;
        }
        return workspaceAccessService.validateAccess(userId, workspaceKey);
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}
