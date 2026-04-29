package com.ssafy.heygent.domain.workspace.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.workspace.dto.request.CreateWorkspaceRequest;
import com.ssafy.heygent.domain.workspace.dto.response.WorkspaceResponse;
import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMember;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMemberStatus;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceRole;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class WorkspaceServiceTest {

    private static final Long USER_ID = 1L;

    @Mock
    private WorkspaceRepository workspaceRepository;

    @Mock
    private WorkspaceMemberRepository workspaceMemberRepository;

    @Mock
    private WorkspaceAccessService workspaceAccessService;

    @InjectMocks
    private WorkspaceService workspaceService;

    @Test
    void createSavesWorkspaceAndOwnerMember() {
        CreateWorkspaceRequest request = request(" 백엔드 프로젝트 ", " Backend-Project ");
        Workspace savedWorkspace = workspace(10L, "backend-project");

        when(workspaceAccessService.normalizeWorkspaceKey(" Backend-Project ")).thenReturn("backend-project");
        when(workspaceRepository.existsByWorkspaceKey("backend-project")).thenReturn(false);
        when(workspaceRepository.save(any(Workspace.class))).thenReturn(savedWorkspace);

        WorkspaceResponse response = workspaceService.create(USER_ID, request);

        ArgumentCaptor<WorkspaceMember> memberCaptor = ArgumentCaptor.forClass(WorkspaceMember.class);
        verify(workspaceMemberRepository).save(memberCaptor.capture());

        assertThat(response.getWorkspaceId()).isEqualTo(10L);
        assertThat(response.getWorkspaceKey()).isEqualTo("backend-project");
        assertThat(response.getName()).isEqualTo("백엔드 프로젝트");
        assertThat(memberCaptor.getValue().getWorkspaceId()).isEqualTo(10L);
        assertThat(memberCaptor.getValue().getUserId()).isEqualTo(USER_ID);
        assertThat(memberCaptor.getValue().getRole()).isEqualTo(WorkspaceRole.OWNER);
    }

    @Test
    void createFailsWhenWorkspaceKeyAlreadyExists() {
        CreateWorkspaceRequest request = request("백엔드 프로젝트", "backend-project");

        when(workspaceAccessService.normalizeWorkspaceKey("backend-project")).thenReturn("backend-project");
        when(workspaceRepository.existsByWorkspaceKey("backend-project")).thenReturn(true);

        assertThatThrownBy(() -> workspaceService.create(USER_ID, request))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.CONFLICT);
    }

    @Test
    void getMyWorkspacesReturnsActiveMemberWorkspaces() {
        WorkspaceMember member = WorkspaceMember.builder()
            .workspaceId(12L)
            .userId(USER_ID)
            .role(WorkspaceRole.OWNER)
            .status(WorkspaceMemberStatus.ACTIVE)
            .build();
        when(workspaceMemberRepository.findByUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
            USER_ID,
            WorkspaceMemberStatus.ACTIVE
        )).thenReturn(List.of(member));
        when(workspaceRepository.findByIdInAndStatus(List.of(12L), WorkspaceStatus.ACTIVE))
            .thenReturn(List.of(workspace(12L, "backend-project")));

        List<WorkspaceResponse> responses = workspaceService.getMyWorkspaces(USER_ID);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getWorkspaceKey()).isEqualTo("backend-project");
    }

    private CreateWorkspaceRequest request(String name, String workspaceKey) {
        CreateWorkspaceRequest request = new CreateWorkspaceRequest();
        ReflectionTestUtils.setField(request, "name", name);
        ReflectionTestUtils.setField(request, "workspaceKey", workspaceKey);
        return request;
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
