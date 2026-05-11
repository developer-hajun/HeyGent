package com.ssafy.heygent.domain.memory.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.entity.UserMemoryEvent;

public interface UserMemoryEventRepository extends JpaRepository<UserMemoryEvent, Long> {

    List<UserMemoryEvent> findByMemoryIdAndUserIdOrderByCreatedAtDesc(Long memoryId, Long userId);

    boolean existsByMemoryIdAndUserIdAndEventTypeAndTaskRunId(
        Long memoryId,
        Long userId,
        MemoryEventType eventType,
        String taskRunId
    );
}
