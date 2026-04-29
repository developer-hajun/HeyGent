package com.ssafy.heygent.domain.integration.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.integration.entity.IntegrationCredential;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredentialStatus;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class IntegrationCredentialResponse {

    private Long credentialId;
    private Long integrationId;
    private String credentialKey;
    private boolean hasSecret;
    private IntegrationCredentialStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static IntegrationCredentialResponse from(IntegrationCredential credential) {
        return IntegrationCredentialResponse.builder()
            .credentialId(credential.getId())
            .integrationId(credential.getIntegrationId())
            .credentialKey(credential.getCredentialKey())
            .hasSecret(credential.getSecretValue() != null)
            .status(credential.getStatus())
            .createdAt(credential.getCreatedAt())
            .updatedAt(credential.getUpdatedAt())
            .build();
    }
}
