package com.ssafy.heygent.domain.integration.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationStatus;

public interface IntegrationRepository extends JpaRepository<Integration, Long> {

    Optional<Integration> findByIdAndOwnerUserIdAndStatus(
        Long id,
        Long ownerUserId,
        IntegrationStatus status
    );

    List<Integration> findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
        Long ownerUserId,
        IntegrationStatus status
    );
}
