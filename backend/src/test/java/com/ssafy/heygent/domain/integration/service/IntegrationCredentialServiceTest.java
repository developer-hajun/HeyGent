package com.ssafy.heygent.domain.integration.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
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
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.request.UpdateIntegrationCredentialRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationCredentialResponse;
import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredential;
import com.ssafy.heygent.domain.integration.entity.IntegrationCredentialStatus;
import com.ssafy.heygent.domain.integration.entity.IntegrationProvider;
import com.ssafy.heygent.domain.integration.entity.IntegrationStatus;
import com.ssafy.heygent.domain.integration.repository.IntegrationCredentialRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class IntegrationCredentialServiceTest {

    private static final Long USER_ID = 1L;
    private static final Long INTEGRATION_ID = 10L;

    @Mock
    private IntegrationService integrationService;

    @Mock
    private IntegrationCredentialRepository integrationCredentialRepository;

    @InjectMocks
    private IntegrationCredentialService integrationCredentialService;

    @Test
    void createSavesCredentialWithoutExposingSecret() {
        CreateIntegrationCredentialRequest request = createRequest(" api-key ", "  secret-value  ");
        Integration integration = integration();
        IntegrationCredential savedCredential = credential(20L, "api-key", "  secret-value  ");

        when(integrationService.findOwnedIntegration(USER_ID, INTEGRATION_ID)).thenReturn(integration);
        when(integrationCredentialRepository.existsByIntegrationIdAndCredentialKeyAndStatus(
            INTEGRATION_ID,
            "api-key",
            IntegrationCredentialStatus.ACTIVE
        )).thenReturn(false);
        when(integrationCredentialRepository.save(any(IntegrationCredential.class))).thenReturn(savedCredential);

        IntegrationCredentialResponse response = integrationCredentialService.create(
            USER_ID,
            INTEGRATION_ID,
            request
        );

        ArgumentCaptor<IntegrationCredential> captor = ArgumentCaptor.forClass(IntegrationCredential.class);
        verify(integrationCredentialRepository).save(captor.capture());
        IntegrationCredential capturedCredential = captor.getValue();

        assertThat(capturedCredential.getIntegrationId()).isEqualTo(INTEGRATION_ID);
        assertThat(capturedCredential.getCredentialKey()).isEqualTo("api-key");
        assertThat(capturedCredential.getSecretValue()).isEqualTo("  secret-value  ");
        assertThat(response.getCredentialId()).isEqualTo(20L);
        assertThat(response.isHasSecret()).isTrue();
    }

    @Test
    void createFailsWhenActiveCredentialKeyAlreadyExists() {
        CreateIntegrationCredentialRequest request = createRequest("api-key", "secret-value");
        when(integrationService.findOwnedIntegration(USER_ID, INTEGRATION_ID)).thenReturn(integration());
        when(integrationCredentialRepository.existsByIntegrationIdAndCredentialKeyAndStatus(
            INTEGRATION_ID,
            "api-key",
            IntegrationCredentialStatus.ACTIVE
        )).thenReturn(true);

        assertThatThrownBy(() -> integrationCredentialService.create(USER_ID, INTEGRATION_ID, request))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.CONFLICT);
    }

    @Test
    void getCredentialsReturnsOnlyActiveCredentials() {
        IntegrationCredential credential = credential(21L, "api-key", "secret-value");
        when(integrationService.findOwnedIntegration(USER_ID, INTEGRATION_ID)).thenReturn(integration());
        when(integrationCredentialRepository.findByIntegrationIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
            INTEGRATION_ID,
            IntegrationCredentialStatus.ACTIVE
        )).thenReturn(List.of(credential));

        List<IntegrationCredentialResponse> responses = integrationCredentialService.getCredentials(
            USER_ID,
            INTEGRATION_ID
        );

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getCredentialKey()).isEqualTo("api-key");
    }

    @Test
    void updateReplacesSecretValue() {
        UpdateIntegrationCredentialRequest request = updateRequest("new-secret");
        IntegrationCredential credential = credential(22L, "api-key", "old-secret");

        when(integrationService.findOwnedIntegration(USER_ID, INTEGRATION_ID)).thenReturn(integration());
        when(integrationCredentialRepository.findByIdAndIntegrationIdAndStatus(
            22L,
            INTEGRATION_ID,
            IntegrationCredentialStatus.ACTIVE
        )).thenReturn(Optional.of(credential));

        IntegrationCredentialResponse response = integrationCredentialService.update(
            USER_ID,
            INTEGRATION_ID,
            22L,
            request
        );

        assertThat(credential.getSecretValue()).isEqualTo("new-secret");
        assertThat(response.getCredentialId()).isEqualTo(22L);
    }

    @Test
    void deleteMarksCredentialDeleted() {
        IntegrationCredential credential = credential(23L, "api-key", "secret-value");

        when(integrationService.findOwnedIntegration(USER_ID, INTEGRATION_ID)).thenReturn(integration());
        when(integrationCredentialRepository.findByIdAndIntegrationIdAndStatus(
            23L,
            INTEGRATION_ID,
            IntegrationCredentialStatus.ACTIVE
        )).thenReturn(Optional.of(credential));

        integrationCredentialService.delete(USER_ID, INTEGRATION_ID, 23L);

        assertThat(credential.getStatus()).isEqualTo(IntegrationCredentialStatus.DELETED);
    }

    private CreateIntegrationCredentialRequest createRequest(String credentialKey, String secretValue) {
        CreateIntegrationCredentialRequest request = new CreateIntegrationCredentialRequest();
        ReflectionTestUtils.setField(request, "credentialKey", credentialKey);
        ReflectionTestUtils.setField(request, "secretValue", secretValue);
        return request;
    }

    private UpdateIntegrationCredentialRequest updateRequest(String secretValue) {
        UpdateIntegrationCredentialRequest request = new UpdateIntegrationCredentialRequest();
        ReflectionTestUtils.setField(request, "secretValue", secretValue);
        return request;
    }

    private Integration integration() {
        return Integration.builder()
            .id(INTEGRATION_ID)
            .ownerUserId(USER_ID)
            .workspaceKey("backend-project")
            .name("Notion")
            .provider(IntegrationProvider.NOTION)
            .status(IntegrationStatus.ACTIVE)
            .build();
    }

    private IntegrationCredential credential(Long id, String credentialKey, String secretValue) {
        return IntegrationCredential.builder()
            .id(id)
            .integrationId(INTEGRATION_ID)
            .credentialKey(credentialKey)
            .secretValue(secretValue)
            .status(IntegrationCredentialStatus.ACTIVE)
            .build();
    }
}
