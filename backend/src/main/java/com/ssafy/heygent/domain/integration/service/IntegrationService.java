package com.ssafy.heygent.domain.integration.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.integration.dto.request.CreateIntegrationRequest;
import com.ssafy.heygent.domain.integration.dto.response.IntegrationResponse;
import com.ssafy.heygent.domain.integration.entity.Integration;
import com.ssafy.heygent.domain.integration.entity.IntegrationStatus;
import com.ssafy.heygent.domain.integration.repository.IntegrationRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class IntegrationService {

    private final IntegrationRepository integrationRepository;
    private final WorkspaceAccessService workspaceAccessService;

    @Transactional
    public IntegrationResponse create(Long userId, CreateIntegrationRequest request) {
        Integration integration = Integration.builder()
            .ownerUserId(userId)
            .workspaceKey(resolveWorkspaceKey(userId, request.getWorkspaceKey()))
            .name(request.getName().trim())
            .provider(request.getProvider())
            .status(IntegrationStatus.ACTIVE)
            .build();

        return IntegrationResponse.from(integrationRepository.save(integration));
    }

    public List<IntegrationResponse> getMyIntegrations(Long userId) {
        return integrationRepository.findByOwnerUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
                userId,
                IntegrationStatus.ACTIVE
            )
            .stream()
            .map(IntegrationResponse::from)
            .toList();
    }

    public IntegrationResponse getIntegration(Long userId, Long integrationId) {
        return IntegrationResponse.from(findOwnedIntegration(userId, integrationId));
    }

    public Integration findOwnedIntegration(Long userId, Long integrationId) {
        if (integrationId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return integrationRepository.findByIdAndOwnerUserIdAndStatus(
                integrationId,
                userId,
                IntegrationStatus.ACTIVE
            )
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }

    private String resolveWorkspaceKey(Long userId, String workspaceKey) {
        if (!StringUtils.hasText(workspaceKey)) {
            return null;
        }
        return workspaceAccessService.validateAccess(userId, workspaceKey);
    }
}
