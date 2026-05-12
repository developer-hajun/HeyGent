package com.ssafy.heygent.domain.ai.openai.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;

import com.ssafy.heygent.domain.ai.openai.entity.AiCommandUsageRecord;

public interface AiCommandUsageRecordRepository extends JpaRepository<AiCommandUsageRecord, Long>,
    JpaSpecificationExecutor<AiCommandUsageRecord> {

    Optional<AiCommandUsageRecord> findByUserIdAndRequestId(Long userId, String requestId);
}
