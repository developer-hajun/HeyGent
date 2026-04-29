package com.ssafy.heygent.domain.workspace.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class WorkspaceResponse {

    private Long workspaceId;
    private String workspaceKey;
    private String name;
    private Long ownerUserId;
    private WorkspaceStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static WorkspaceResponse from(Workspace workspace) {
        return WorkspaceResponse.builder()
            .workspaceId(workspace.getId())
            .workspaceKey(workspace.getWorkspaceKey())
            .name(workspace.getName())
            .ownerUserId(workspace.getOwnerUserId())
            .status(workspace.getStatus())
            .createdAt(workspace.getCreatedAt())
            .updatedAt(workspace.getUpdatedAt())
            .build();
    }
}
