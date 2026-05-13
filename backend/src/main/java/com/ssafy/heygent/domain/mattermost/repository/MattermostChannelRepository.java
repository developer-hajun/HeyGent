package com.ssafy.heygent.domain.mattermost.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.mattermost.entity.MattermostChannel;

public interface MattermostChannelRepository extends JpaRepository<MattermostChannel, Long> {

    List<MattermostChannel> findAllByUserIdOrderByCreatedAtDesc(Long userId);

    Optional<MattermostChannel> findByIdAndUserId(Long id, Long userId);

    Optional<MattermostChannel> findByUserIdAndAliasIgnoreCase(Long userId, String alias);

    Optional<MattermostChannel> findByUserIdAndDefaultChannelTrue(Long userId);

    boolean existsByUserIdAndAliasIgnoreCase(Long userId, String alias);
}
