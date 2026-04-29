package com.ssafy.heygent.domain.workspace.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.workspace.entity.WorkspaceMember;
import com.ssafy.heygent.domain.workspace.entity.WorkspaceMemberStatus;

public interface WorkspaceMemberRepository extends JpaRepository<WorkspaceMember, Long> {

    boolean existsByWorkspaceIdAndUserIdAndStatus(
        Long workspaceId,
        Long userId,
        WorkspaceMemberStatus status
    );

    List<WorkspaceMember> findByUserIdAndStatusOrderByUpdatedAtDescCreatedAtDesc(
        Long userId,
        WorkspaceMemberStatus status
    );
}
