package com.ssafy.heygent.domain.workspace.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMemberStatus;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceMemberRepository;
import com.ssafy.heygent.domain.workspace.repository.WorkspaceRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class WorkspaceAccessService {

    private final WorkspaceRepository workspaceRepository;
    private final WorkspaceMemberRepository workspaceMemberRepository;

    public String validateAccess(Long userId, String workspaceKey) {
        String normalizedWorkspaceKey = normalizeWorkspaceKey(workspaceKey);
        Workspace workspace = workspaceRepository.findByWorkspaceKeyAndStatus(
                normalizedWorkspaceKey,
                WorkspaceStatus.ACTIVE
            )
            .orElseThrow(() -> new CustomException(ErrorCode.ACCESS_DENIED));

        boolean accessible = workspaceMemberRepository.existsByWorkspaceIdAndUserIdAndStatus(
            workspace.getId(),
            userId,
            WorkspaceMemberStatus.ACTIVE
        );
        if (!accessible) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }
        return normalizedWorkspaceKey;
    }

    public String normalizeWorkspaceKey(String workspaceKey) {
        if (!StringUtils.hasText(workspaceKey)) {
            return null;
        }
        return workspaceKey.trim().toLowerCase();
    }
}
