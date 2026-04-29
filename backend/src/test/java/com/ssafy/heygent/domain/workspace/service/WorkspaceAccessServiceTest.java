package com.ssafy.heygent.domain.workspace.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMemberStatus;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class WorkspaceAccessServiceTest {

    private static final Long USER_ID = 1L;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @InjectMocks
    private WorkspaceAccessService workspaceAccessService;

    @Test
    void validateAccessReturnsNormalizedWorkspaceKeyWhenUserIsActiveMember() {
        Workspace workspace = workspace(10L, "backend-project");
        when(workspaceRepository.findByWorkspaceKeyAndStatus("backend-project", WorkspaceStatus.ACTIVE))
            .thenReturn(Optional.of(workspace));
        when(workspaceMemberRepository.existsByWorkspaceIdAndUserIdAndStatus(
            10L,
            USER_ID,
            WorkspaceMemberStatus.ACTIVE
        )).thenReturn(true);

        String workspaceKey = workspaceAccessService.validateAccess(USER_ID, " Backend-Project ");

        assertThat(workspaceKey).isEqualTo("backend-project");
    }

    @Test
    void validateAccessFailsWhenWorkspaceDoesNotExist() {
        when(workspaceRepository.findByWorkspaceKeyAndStatus("missing", WorkspaceStatus.ACTIVE))
            .thenReturn(Optional.empty());

        assertThatThrownBy(() -> workspaceAccessService.validateAccess(USER_ID, "missing"))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.ACCESS_DENIED);
    }

    @Test
    void validateAccessFailsWhenUserIsNotMember() {
        Workspace workspace = workspace(11L, "backend-project");
        when(workspaceRepository.findByWorkspaceKeyAndStatus("backend-project", WorkspaceStatus.ACTIVE))
            .thenReturn(Optional.of(workspace));
        when(workspaceMemberRepository.existsByWorkspaceIdAndUserIdAndStatus(
            11L,
            USER_ID,
            WorkspaceMemberStatus.ACTIVE
        )).thenReturn(false);

        assertThatThrownBy(() -> workspaceAccessService.validateAccess(USER_ID, "backend-project"))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.ACCESS_DENIED);
    }

    private Workspace workspace(Long id, String workspaceKey) {
        return Workspace.builder()
            .id(id)
            .workspaceKey(workspaceKey)
            .name("백엔드 프로젝트")
            .ownerUserId(USER_ID)
            .status(WorkspaceStatus.ACTIVE)
            .build();
    }
}
