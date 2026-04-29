package com.ssafy.heygent.domain.integration.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.integration.entity.IntegrationCredential;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredentialStatus;

public interface IntegrationCredentialRepository extends JpaRepository<IntegrationCredential, Long> {

    boolean existsByIntegrationIdAndCredentialKeyAndStatus(
        Long integrationId,
        String credentialKey,
        IntegrationCredentialStatus status
    );

    Optional<IntegrationCredential> findByIdAndIntegrationIdAndStatus(
        Long id,
        Long integrationId,
        IntegrationCredentialStatus status
    );

    List<IntegrationCredential> findByIntegrationIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
        Long integrationId,
        IntegrationCredentialStatus status
    );
}
