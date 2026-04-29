package com.ssafy.heygent.domain.agent.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileStatus;
import com.ssafy.heygent.domain.agent.entity.AgentProfileType;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AgentProfileResponse {

    private Long agentProfileId;
    private Long ownerUserId;
    private String workspaceKey;
    private String name;
    private AgentProfileType type;
    private String model;
    private String systemPrompt;
    private AgentProfileStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static AgentProfileResponse from(AgentProfile agentProfile) {
        return AgentProfileResponse.builder()
            .agentProfileId(agentProfile.getId())
            .ownerUserId(agentProfile.getOwnerUserId())
            .workspaceKey(agentProfile.getWorkspaceKey())
            .name(agentProfile.getName())
            .type(agentProfile.getType())
            .model(agentProfile.getModel())
            .systemPrompt(agentProfile.getSystemPrompt())
            .status(agentProfile.getStatus())
            .createdAt(agentProfile.getCreatedAt())
            .updatedAt(agentProfile.getUpdatedAt())
            .build();
    }
}
