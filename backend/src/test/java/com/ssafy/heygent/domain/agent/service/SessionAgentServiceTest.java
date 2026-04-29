package com.ssafy.heygent.domain.agent.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileStatus;
import com.ssafy.heygent.domain.agent.entity.AgentProfileType;
import com.ssafy.heygent.domain.agent.entity.SessionSubAgent;
import com.ssafy.heygent.domain.agent.repository.AgentProfileRepository;
import com.ssafy.heygent.domain.agent.repository.SessionSubAgentRepository;
import com.ssafy.heygent.domain.session.entity.ProductSession;
import com.ssafy.heygent.domain.session.entity.ProductSessionStatus;
import com.ssafy.heygent.domain.session.service.ProductSessionService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class SessionAgentServiceTest {

    private static final Long USER_ID = 1L;
    private static final Long SESSION_ID = 10L;

    @Mock
    private ProductSessionService productSessionService;

    @Mock
    private AgentProfileService agentProfileService;

    @Mock
    private AgentProfileRepository agentProfileRepository;

    @Mock
    private SessionSubAgentRepository sessionSubAgentRepository;

    @InjectMocks
    private SessionAgentService sessionAgentService;

    @Test
    void connectMainAgentSetsMainAgentProfileId() {
        ProductSession session = session("backend-project");
        AgentProfile agentProfile = agentProfile(20L, AgentProfileType.MAIN, "backend-project");

        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session);
        when(agentProfileService.findOwnedAgentProfile(USER_ID, 20L)).thenReturn(agentProfile);

        AgentProfileResponse response = sessionAgentService.connectMainAgent(USER_ID, SESSION_ID, 20L);

        verify(agentProfileService).validateWorkspaceBoundary("backend-project", agentProfile);
        assertThat(session.getMainAgentProfileId()).isEqualTo(20L);
        assertThat(response.getAgentProfileId()).isEqualTo(20L);
    }

    @Test
    void connectMainAgentFailsWhenProfileTypeIsNotMain() {
        ProductSession session = session(null);
        AgentProfile agentProfile = agentProfile(21L, AgentProfileType.SUBAGENT, null);

        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session);
        when(agentProfileService.findOwnedAgentProfile(USER_ID, 21L)).thenReturn(agentProfile);

        assertThatThrownBy(() -> sessionAgentService.connectMainAgent(USER_ID, SESSION_ID, 21L))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.INVALID_INPUT_VALUE);
    }

    @Test
    void connectSubAgentSavesMappingWhenNotExists() {
        ProductSession session = session("backend-project");
        AgentProfile agentProfile = agentProfile(22L, AgentProfileType.SUBAGENT, "backend-project");

        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session);
        when(agentProfileService.findOwnedAgentProfile(USER_ID, 22L)).thenReturn(agentProfile);
        when(sessionSubAgentRepository.existsBySessionIdAndAgentProfileId(SESSION_ID, 22L)).thenReturn(false);

        sessionAgentService.connectSubAgent(USER_ID, SESSION_ID, 22L);

        ArgumentCaptor<SessionSubAgent> captor = ArgumentCaptor.forClass(SessionSubAgent.class);
        verify(sessionSubAgentRepository).save(captor.capture());
        assertThat(captor.getValue().getSessionId()).isEqualTo(SESSION_ID);
        assertThat(captor.getValue().getAgentProfileId()).isEqualTo(22L);
    }

    @Test
    void connectSubAgentDoesNotDuplicateMapping() {
        ProductSession session = session(null);
        AgentProfile agentProfile = agentProfile(23L, AgentProfileType.SUBAGENT, null);

        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session);
        when(agentProfileService.findOwnedAgentProfile(USER_ID, 23L)).thenReturn(agentProfile);
        when(sessionSubAgentRepository.existsBySessionIdAndAgentProfileId(SESSION_ID, 23L)).thenReturn(true);

        sessionAgentService.connectSubAgent(USER_ID, SESSION_ID, 23L);

        verify(sessionSubAgentRepository, never()).save(any(SessionSubAgent.class));
    }

    @Test
    void disconnectSubAgentDeletesMapping() {
        SessionSubAgent sessionSubAgent = SessionSubAgent.builder()
            .id(30L)
            .sessionId(SESSION_ID)
            .agentProfileId(24L)
            .build();
        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session(null));
        when(sessionSubAgentRepository.findBySessionIdAndAgentProfileId(SESSION_ID, 24L))
            .thenReturn(Optional.of(sessionSubAgent));

        sessionAgentService.disconnectSubAgent(USER_ID, SESSION_ID, 24L);

        verify(sessionSubAgentRepository).delete(sessionSubAgent);
    }

    @Test
    void getSubAgentsReturnsOwnedProfilesInMappingOrder() {
        SessionSubAgent first = SessionSubAgent.builder().sessionId(SESSION_ID).agentProfileId(25L).build();
        SessionSubAgent second = SessionSubAgent.builder().sessionId(SESSION_ID).agentProfileId(26L).build();
        AgentProfile firstProfile = agentProfile(25L, AgentProfileType.SUBAGENT, null);
        AgentProfile secondProfile = agentProfile(26L, AgentProfileType.SUBAGENT, null);

        when(productSessionService.findOwnedSession(USER_ID, SESSION_ID)).thenReturn(session(null));
        when(sessionSubAgentRepository.findBySessionIdOrderByCreatedAtAsc(SESSION_ID)).thenReturn(List.of(first, second));
        when(agentProfileRepository.findAllById(List.of(25L, 26L))).thenReturn(List.of(secondProfile, firstProfile));

        List<AgentProfileResponse> responses = sessionAgentService.getSubAgents(USER_ID, SESSION_ID);

        assertThat(responses).extracting(AgentProfileResponse::getAgentProfileId).containsExactly(25L, 26L);
    }

    private ProductSession session(String workspaceKey) {
        return ProductSession.builder()
            .id(SESSION_ID)
            .userId(USER_ID)
            .title("회의 정리")
            .workspaceKey(workspaceKey)
            .status(ProductSessionStatus.ACTIVE)
            .build();
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
