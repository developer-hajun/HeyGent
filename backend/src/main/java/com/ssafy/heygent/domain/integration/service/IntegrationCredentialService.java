package com.ssafy.heygent.domain.integration.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.request.UpdateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationCredentialResponse;
import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredential;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredentialStatus;
import com.ssafy.heygent.domain.integration.repository.IntegrationCredentialRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class IntegrationCredentialService {

    private final IntegrationService integrationService;
    private final IntegrationCredentialRepository integrationCredentialRepository;

    @Transactional
    public IntegrationCredentialResponse create(
        Long userId,
        Long integrationId,
        CreateIntegrationCredentialRequest request
    ) {
        Integration integration = integrationService.findOwnedIntegration(userId, integrationId);
        String credentialKey = request.getCredentialKey().trim();
        if (integrationCredentialRepository.existsByIntegrationIdAndCredentialKeyAndStatus(
            integration.getId(),
            credentialKey,
            IntegrationCredentialStatus.ACTIVE
        )) {
            throw new CustomException(ErrorCode.CONFLICT);
        }

        IntegrationCredential credential = IntegrationCredential.builder()
            .integrationId(integration.getId())
            .credentialKey(credentialKey)
            .secretValue(request.getSecretValue())
            .status(IntegrationCredentialStatus.ACTIVE)
            .build();

        return IntegrationCredentialResponse.from(integrationCredentialRepository.save(credential));
    }

    public List<IntegrationCredentialResponse> getCredentials(Long userId, Long integrationId) {
        Integration integration = integrationService.findOwnedIntegration(userId, integrationId);
        return integrationCredentialRepository.findByIntegrationIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
                integration.getId(),
                IntegrationCredentialStatus.ACTIVE
            )
            .stream()
            .map(IntegrationCredentialResponse::from)
            .toList();
    }

    @Transactional
    public IntegrationCredentialResponse update(
        Long userId,
        Long integrationId,
        Long credentialId,
        UpdateIntegrationCredentialRequest request
    ) {
        IntegrationCredential credential = findOwnedCredential(userId, integrationId, credentialId);
        credential.updateSecretValue(request.getSecretValue());
        return IntegrationCredentialResponse.from(credential);
    }

    @Transactional
    public void delete(Long userId, Long integrationId, Long credentialId) {
        IntegrationCredential credential = findOwnedCredential(userId, integrationId, credentialId);
        credential.delete();
    }

    private IntegrationCredential findOwnedCredential(Long userId, Long integrationId, Long credentialId) {
        Integration integration = integrationService.findOwnedIntegration(userId, integrationId);
        if (credentialId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return integrationCredentialRepository.findByIdAndIntegrationIdAndStatus(
                credentialId,
                integration.getId(),
                IntegrationCredentialStatus.ACTIVE
            )
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }
}
