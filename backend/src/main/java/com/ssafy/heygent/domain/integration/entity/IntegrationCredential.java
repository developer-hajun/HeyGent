package com.ssafy.heygent.domain.integration.entity;

import java.time.LocalDateTime;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@Table(
    name = "integration_credentials",
    uniqueConstraints = @UniqueConstraint(columnNames = {"integration_id", "credential_key"})
)
@EntityListeners(AuditingEntityListener.class)
public class IntegrationCredential {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "integration_id", nullable = false)
    private Long integrationId;

    @Column(name = "credential_key", nullable = false, length = 100)
    private String credentialKey;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String secretValue;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private IntegrationCredentialStatus status;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    public void updateSecretValue(String secretValue) {
        this.secretValue = secretValue;
        this.status = IntegrationCredentialStatus.ACTIVE;
    }

    public void delete() {
        this.status = IntegrationCredentialStatus.DELETED;
    }
}
