package com.ssafy.heygent.domain.agent.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.agent.entity.SessionSubAgent;

public interface SessionSubAgentRepository extends JpaRepository<SessionSubAgent, Long> {

    boolean existsBySessionIdAndAgentProfileId(Long sessionId, Long agentProfileId);

    Optional<SessionSubAgent> findBySessionIdAndAgentProfileId(Long sessionId, Long agentProfileId);

    List<SessionSubAgent> findBySessionIdOrderByCreatedAtAsc(Long sessionId);
}
