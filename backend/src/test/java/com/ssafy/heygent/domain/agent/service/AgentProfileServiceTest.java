package com.ssafy.heygent.domain.agent.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.agent.dto.request.CreateAgentProfileRequest;
import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileStatus;
import com.ssafy.heygent.domain.agent.entity.AgentProfileType;
import com.ssafy.heygent.domain.agent.repository.AgentProfileRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class AgentProfileServiceTest {

    private static final Long USER_ID = 1L;

    @Mock
    private AgentProfileRepository agentProfileRepository;

    @Mock
    private WorkspaceAccessService workspaceAccessService;

    @InjectMocks
    private AgentProfileService agentProfileService;

    @Test
    void createSavesAgentProfileWithWorkspaceAccessValidation() {
        CreateAgentProfileRequest request = request(
            " 리서치 에이전트 ",
            AgentProfileType.SUBAGENT,
            " Backend-Project ",
            "gpt-test",
            "자료를 조사한다."
        );
        AgentProfile savedAgentProfile = agentProfile(10L, AgentProfileType.SUBAGENT, "backend-project");

        when(workspaceAccessService.validateAccess(USER_ID, " Backend-Project ")).thenReturn("backend-project");
        when(agentProfileRepository.save(any(AgentProfile.class))).thenReturn(savedAgentProfile);

        AgentProfileResponse response = agentProfileService.create(USER_ID, request);

        ArgumentCaptor<AgentProfile> captor = ArgumentCaptor.forClass(AgentProfile.class);
        org.mockito.Mockito.verify(agentProfileRepository).save(captor.capture());
        AgentProfile capturedAgentProfile = captor.getValue();

        assertThat(capturedAgentProfile.getOwnerUserId()).isEqualTo(USER_ID);
        assertThat(capturedAgentProfile.getName()).isEqualTo("리서치 에이전트");
        assertThat(capturedAgentProfile.getWorkspaceKey()).isEqualTo("backend-project");
        assertThat(capturedAgentProfile.getType()).isEqualTo(AgentProfileType.SUBAGENT);
        assertThat(response.getAgentProfileId()).isEqualTo(10L);
    }

    @Test
    void getMyAgentProfilesReturnsActiveProfiles() {
        AgentProfile agentProfile = agentProfile(11L, AgentProfileType.MAIN, null);
        when(agentProfileRepository.findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
            USER_ID,
            AgentProfileStatus.ACTIVE
        )).thenReturn(List.of(agentProfile));

        List<AgentProfileResponse> responses = agentProfileService.getMyAgentProfiles(USER_ID);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getAgentProfileId()).isEqualTo(11L);
    }

    @Test
    void findOwnedAgentProfileFailsWhenProfileIsNotOwned() {
        when(agentProfileRepository.findByIdAndOwnerUserIdAndStatus(12L, USER_ID, AgentProfileStatus.ACTIVE))
            .thenReturn(Optional.empty());

        assertThatThrownBy(() -> agentProfileService.findOwnedAgentProfile(USER_ID, 12L))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    @Test
    void validateWorkspaceBoundaryFailsWhenProfileWorkspaceDoesNotMatchSession() {
        AgentProfile agentProfile = agentProfile(13L, AgentProfileType.MAIN, "other-workspace");

        assertThatThrownBy(() -> agentProfileService.validateWorkspaceBoundary("backend-project", agentProfile))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.ACCESS_DENIED);
    }

    private CreateAgentProfileRequest request(
        String name,
        AgentProfileType type,
        String workspaceKey,
        String model,
        String systemPrompt
    ) {
        CreateAgentProfileRequest request = new CreateAgentProfileRequest();
        ReflectionTestUtils.setField(request, "name", name);
        ReflectionTestUtils.setField(request, "type", type);
        ReflectionTestUtils.setField(request, "workspaceKey", workspaceKey);
        ReflectionTestUtils.setField(request, "model", model);
        ReflectionTestUtils.setField(request, "systemPrompt", systemPrompt);
        return request;
    }

    private AgentProfile agentProfile(Long id, AgentProfileType type, String workspaceKey) {
        return AgentProfile.builder()
            .id(id)
            .ownerUserId(USER_ID)
            .workspaceKey(workspaceKey)
            .name("리서치 에이전트")
            .type(type)
            .model("gpt-test")
            .systemPrompt("자료를 조사한다.")
            .status(AgentProfileStatus.ACTIVE)
            .build();
    }
}
