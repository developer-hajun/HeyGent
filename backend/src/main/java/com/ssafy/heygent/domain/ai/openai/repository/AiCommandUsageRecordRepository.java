package com.ssafy.heygent.domain.ai.openai.repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.ssafy.heygent.domain.ai.openai.entity.AiCommandUsageRecord;

public interface AiCommandUsageRecordRepository extends JpaRepository<AiCommandUsageRecord, Long> {

    Optional<AiCommandUsageRecord> findByUserIdAndRequestId(Long userId, String requestId);

    @Query("""
        SELECT record
        FROM AiCommandUsageRecord record
        WHERE record.userId = :userId
          AND (:taskRunId IS NULL OR record.taskRunId = :taskRunId)
          AND (:sessionId IS NULL OR record.sessionId = :sessionId)
          AND (:fromDateTime IS NULL OR record.createdAt >= :fromDateTime)
          AND (:toDateTime IS NULL OR record.createdAt < :toDateTime)
        ORDER BY record.createdAt DESC
        """)
    List<AiCommandUsageRecord> findUsageRecords(
        @Param("userId") Long userId,
        @Param("taskRunId") String taskRunId,
        @Param("sessionId") String sessionId,
        @Param("fromDateTime") LocalDateTime fromDateTime,
        @Param("toDateTime") LocalDateTime toDateTime,
        Pageable pageable
    );
}
