package com.ssafy.heygent.domain.agent.service;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.agent.dto.response.AgentProfileResponse;
import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileType;
import com.ssafy.heygent.domain.agent.entity.SessionSubAgent;
import com.ssafy.heygent.domain.agent.repository.AgentProfileRepository;
import com.ssafy.heygent.domain.agent.repository.SessionSubAgentRepository;
import com.ssafy.heygent.domain.session.entity.ProductSession;
import com.ssafy.heygent.domain.session.service.ProductSessionService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class SessionAgentService {

    private final ProductSessionService productSessionService;
    private final AgentProfileService agentProfileService;
    private final AgentProfileRepository agentProfileRepository;
    private final SessionSubAgentRepository sessionSubAgentRepository;

    @Transactional
    public AgentProfileResponse connectMainAgent(Long userId, Long sessionId, Long agentProfileId) {
        ProductSession session = productSessionService.findOwnedSession(userId, sessionId);
        AgentProfile agentProfile = agentProfileService.findOwnedAgentProfile(userId, agentProfileId);
        validateAgentType(agentProfile, AgentProfileType.MAIN);
        agentProfileService.validateWorkspaceBoundary(session.getWorkspaceKey(), agentProfile);

        session.connectMainAgent(agentProfile.getId());
        return AgentProfileResponse.from(agentProfile);
    }

    @Transactional
    public AgentProfileResponse connectSubAgent(Long userId, Long sessionId, Long agentProfileId) {
        ProductSession session = productSessionService.findOwnedSession(userId, sessionId);
        AgentProfile agentProfile = agentProfileService.findOwnedAgentProfile(userId, agentProfileId);
        validateAgentType(agentProfile, AgentProfileType.SUBAGENT);
        agentProfileService.validateWorkspaceBoundary(session.getWorkspaceKey(), agentProfile);

        if (!sessionSubAgentRepository.existsBySessionIdAndAgentProfileId(sessionId, agentProfileId)) {
            sessionSubAgentRepository.save(SessionSubAgent.builder()
                .sessionId(sessionId)
                .agentProfileId(agentProfileId)
                .build());
        }
        return AgentProfileResponse.from(agentProfile);
    }

    @Transactional
    public void disconnectSubAgent(Long userId, Long sessionId, Long agentProfileId) {
        productSessionService.findOwnedSession(userId, sessionId);
        SessionSubAgent sessionSubAgent = sessionSubAgentRepository.findBySessionIdAndAgentProfileId(
                sessionId,
                agentProfileId
            )
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
        sessionSubAgentRepository.delete(sessionSubAgent);
    }

    public AgentProfileResponse getMainAgent(Long userId, Long sessionId) {
        ProductSession session = productSessionService.findOwnedSession(userId, sessionId);
        if (session.getMainAgentProfileId() == null) {
            throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        AgentProfile agentProfile = agentProfileService.findOwnedAgentProfile(userId, session.getMainAgentProfileId());
        return AgentProfileResponse.from(agentProfile);
    }

    public List<AgentProfileResponse> getSubAgents(Long userId, Long sessionId) {
        productSessionService.findOwnedSession(userId, sessionId);
        List<Long> agentProfileIds = sessionSubAgentRepository.findBySessionIdOrderByCreatedAtAsc(sessionId).stream()
            .map(SessionSubAgent::getAgentProfileId)
            .toList();
        Map<Long, AgentProfile> agentProfileById = agentProfileRepository.findAllById(agentProfileIds).stream()
            .filter(agentProfile -> Objects.equals(agentProfile.getOwnerUserId(), userId))
            .collect(Collectors.toMap(AgentProfile::getId, Function.identity()));

        return agentProfileIds.stream()
            .map(agentProfileById::get)
            .filter(Objects::nonNull)
            .map(AgentProfileResponse::from)
            .toList();
    }

    private void validateAgentType(AgentProfile agentProfile, AgentProfileType expectedType) {
        if (agentProfile.getType() != expectedType) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }
}
