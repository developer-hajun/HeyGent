package com.ssafy.heygent.domain.agent.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.agent.entity.AgentProfile;
import com.ssafy.heygent.domain.agent.entity.AgentProfileStatus;

public interface AgentProfileRepository extends JpaRepository<AgentProfile, Long> {

    Optional<AgentProfile> findByIdAndOwnerUserIdAndStatus(
        Long id,
        Long ownerUserId,
        AgentProfileStatus status
    );

    List<AgentProfile> findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
        Long ownerUserId,
        AgentProfileStatus status
    );
}
