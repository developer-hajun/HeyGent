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

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationResponse;
import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationProvider;
import com.ssafy.heygent.domain.integration.entity.IntegrationStatus;
import com.ssafy.heygent.domain.integration.repository.IntegrationRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class IntegrationServiceTest {

    private static final Long USER_ID = 1L;

    @Mock
    private IntegrationRepository integrationRepository;

    @Mock
    private WorkspaceAccessService workspaceAccessService;

    @InjectMocks
    private IntegrationService integrationService;

    @Test
    void createSavesIntegrationWithWorkspaceAccessValidation() {
        CreateIntegrationRequest request = request(" Notion 연동 ", IntegrationProvider.NOTION, " Backend-Project ");
        Integration savedIntegration = integration(10L, "Notion 연동", "backend-project");

        when(workspaceAccessService.validateAccess(USER_ID, " Backend-Project ")).thenReturn("backend-project");
        when(integrationRepository.save(any(Integration.class))).thenReturn(savedIntegration);

        IntegrationResponse response = integrationService.create(USER_ID, request);

        ArgumentCaptor<Integration> captor = ArgumentCaptor.forClass(Integration.class);
        verify(integrationRepository).save(captor.capture());
        Integration capturedIntegration = captor.getValue();

        assertThat(capturedIntegration.getOwnerUserId()).isEqualTo(USER_ID);
        assertThat(capturedIntegration.getName()).isEqualTo("Notion 연동");
        assertThat(capturedIntegration.getWorkspaceKey()).isEqualTo("backend-project");
        assertThat(capturedIntegration.getProvider()).isEqualTo(IntegrationProvider.NOTION);
        assertThat(response.getIntegrationId()).isEqualTo(10L);
    }

    @Test
    void getMyIntegrationsReturnsActiveIntegrations() {
        Integration integration = integration(11L, "Notion 연동", null);
        when(integrationRepository.findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
            USER_ID,
            IntegrationStatus.ACTIVE
        )).thenReturn(List.of(integration));

        List<IntegrationResponse> responses = integrationService.getMyIntegrations(USER_ID);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getIntegrationId()).isEqualTo(11L);
    }

    @Test
    void findOwnedIntegrationFailsWhenIntegrationIsNotOwned() {
        when(integrationRepository.findByIdAndOwnerUserIdAndStatus(12L, USER_ID, IntegrationStatus.ACTIVE))
            .thenReturn(Optional.empty());

        assertThatThrownBy(() -> integrationService.findOwnedIntegration(USER_ID, 12L))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    private CreateIntegrationRequest request(
        String name,
        IntegrationProvider provider,
        String workspaceKey
    ) {
        CreateIntegrationRequest request = new CreateIntegrationRequest();
        ReflectionTestUtils.setField(request, "name", name);
        ReflectionTestUtils.setField(request, "provider", provider);
        ReflectionTestUtils.setField(request, "workspaceKey", workspaceKey);
        return request;
    }

    private Integration integration(Long id, String name, String workspaceKey) {
        return Integration.builder()
            .id(id)
            .ownerUserId(USER_ID)
            .workspaceKey(workspaceKey)
            .name(name)
            .provider(IntegrationProvider.NOTION)
            .status(IntegrationStatus.ACTIVE)
            .build();
    }
}
