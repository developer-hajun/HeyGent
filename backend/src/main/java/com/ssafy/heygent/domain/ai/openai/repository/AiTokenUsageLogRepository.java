package com.ssafy.heygent.domain.ai.openai.repository;

import java.time.LocalDateTime;
import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.ssafy.heygent.domain.ai.openai.entity.AiTokenUsageLog;

public interface AiTokenUsageLogRepository extends JpaRepository<AiTokenUsageLog, Long> {

    @Query("""
        select usageLog
        from AiTokenUsageLog usageLog
        where usageLog.userId = :userId
            and (:fromDateTime is null or usageLog.createdAt >= :fromDateTime)
            and (:toDateTime is null or usageLog.createdAt < :toDateTime)
        order by usageLog.createdAt asc
        """)
    List<AiTokenUsageLog> findUserLogs(
        @Param("userId") Long userId,
        @Param("fromDateTime") LocalDateTime fromDateTime,
        @Param("toDateTime") LocalDateTime toDateTime
    );
}
