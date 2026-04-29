package com.ssafy.heygent.domain.agent.dto.request;

import com.ssafy.heygent.domain.agent.entity.AgentProfileType;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateAgentProfileRequest {

    @NotBlank(message = "Agent 이름은 필수입니다.")
    @Size(max = 100, message = "Agent 이름은 100자 이하여야 합니다.")
    private String name;

    @NotNull(message = "Agent 타입은 필수입니다.")
    private AgentProfileType type;

    @Size(max = 100, message = "Workspace Key는 100자 이하여야 합니다.")
    private String workspaceKey;

    @Size(max = 100, message = "모델명은 100자 이하여야 합니다.")
    private String model;

    @Size(max = 4000, message = "System Prompt는 4000자 이하여야 합니다.")
    private String systemPrompt;
}
