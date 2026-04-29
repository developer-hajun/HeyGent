package com.ssafy.heygent.domain.workspace.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.workspace.dto.request.CreateWorkspaceRequest;
import com.ssafy.heygent.domain.workspace.dto.response.WorkspaceResponse;
import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMember;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMemberStatus;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceRole;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class WorkspaceService {

    private static final String GENERATED_WORKSPACE_KEY_PREFIX = "ws-";
    private static final int GENERATED_WORKSPACE_KEY_LENGTH = 12;

    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;
    private final WorkspaceAccessService workspaceAccessService;

    @Transactional
    public WorkspaceResponse create(Long userId, CreateWorkspaceRequest request) {
        String workspaceKey = resolveWorkspaceKey(request.getWorkspaceKey());
        if (workspaceRepository.existsByWorkspaceKey(workspaceKey)) {
            throw new CustomException(ErrorCode.CONFLICT);
        }

        Workspace workspace = workspaceRepository.save(Workspace.builder()
            .workspaceKey(workspaceKey)
            .name(request.getName().trim())
            .ownerUserId(userId)
            .status(WorkspaceStatus.ACTIVE)
            .build());

        workspaceMemberRepository.save(WorkspaceMember.builder()
            .workspaceId(workspace.getId())
            .userId(userId)
            .role(WorkspaceRole.OWNER)
            .status(WorkspaceMemberStatus.ACTIVE)
            .build());

        return WorkspaceResponse.from(workspace);
    }

    public List<WorkspaceResponse> getMyWorkspaces(Long userId) {
        List<Long> workspaceIds = workspaceMemberRepository.findByUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
                userId,
                WorkspaceMemberStatus.ACTIVE
            )
            .stream()
            .map(WorkspaceMember::getWorkspaceId)
            .toList();
        Map<Long, Workspace> workspaceById = workspaceRepository.findByIdInAndStatus(
                workspaceIds,
                WorkspaceStatus.ACTIVE
            )
            .stream()
            .collect(LinkedHashMap::new, (map, workspace) -> map.put(workspace.getId(), workspace), Map::putAll);

        return workspaceIds.stream()
            .map(workspaceById::get)
            .filter(workspace -> workspace != null)
            .map(WorkspaceResponse::from)
            .toList();
    }

    public WorkspaceResponse getWorkspace(Long userId, String workspaceKey) {
        String normalizedWorkspaceKey = workspaceAccessService.validateAccess(userId, workspaceKey);
        Workspace workspace = workspaceRepository.findByWorkspaceKeyAndStatus(
                normalizedWorkspaceKey,
                WorkspaceStatus.ACTIVE
            )
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
        return WorkspaceResponse.from(workspace);
    }

    private String resolveWorkspaceKey(String workspaceKey) {
        String normalizedWorkspaceKey = workspaceAccessService.normalizeWorkspaceKey(workspaceKey);
        if (normalizedWorkspaceKey != null) {
            return normalizedWorkspaceKey;
        }
        return generateWorkspaceKey();
    }

    private String generateWorkspaceKey() {
        String workspaceKey;
        do {
            workspaceKey = GENERATED_WORKSPACE_KEY_PREFIX + UUID.randomUUID()
                .toString()
                .replace("-", "")
                .substring(0, GENERATED_WORKSPACE_KEY_LENGTH);
        } while (workspaceRepository.existsByWorkspaceKey(workspaceKey));
        return workspaceKey;
    }
}
