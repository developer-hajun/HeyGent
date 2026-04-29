package com.ssafy.heygent.domain.integration.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationProvider;
import com.ssafy.heygent.domain.integration.entity.IntegrationStatus;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class IntegrationResponse {

    private Long integrationId;
    private Long ownerUserId;
    private String workspaceKey;
    private String name;
    private IntegrationProvider provider;
    private IntegrationStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static IntegrationResponse from(Integration integration) {
        return IntegrationResponse.builder()
            .integrationId(integration.getId())
            .ownerUserId(integration.getOwnerUserId())
            .workspaceKey(integration.getWorkspaceKey())
            .name(integration.getName())
            .provider(integration.getProvider())
            .status(integration.getStatus())
            .createdAt(integration.getCreatedAt())
            .updatedAt(integration.getUpdatedAt())
            .build();
    }
}
