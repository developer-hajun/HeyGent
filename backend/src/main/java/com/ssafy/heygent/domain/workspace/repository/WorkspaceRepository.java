package com.ssafy.heygent.domain.workspace.repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.workspace.entity.Workspace;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceStatus;

public interface WorkspaceRepository extends JpaRepository<Workspace, Long> {

    boolean existsByWorkspaceKey(String workspaceKey);

    Optional<Workspace> findByWorkspaceKeyAndStatus(String workspaceKey, WorkspaceStatus status);

    List<Workspace> findByIdInAndStatus(Collection<Long> ids, WorkspaceStatus status);
}
