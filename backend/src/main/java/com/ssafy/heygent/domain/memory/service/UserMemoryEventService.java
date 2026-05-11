package com.ssafy.heygent.domain.memory.service;

import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;
import com.ssafy.heygent.domain.memory.entity.UserMemoryEvent;
import com.ssafy.heygent.domain.memory.repository.UserMemoryEventRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional
public class UserMemoryEventService {

    private final UserMemoryEventRepository userMemoryEventRepository;

    public void record(UserMemory memory, MemoryEventType eventType) {
        record(memory, eventType, null, Map.of());
    }

    public void record(
        UserMemory memory,
        MemoryEventType eventType,
        Double score,
        Map<String, Object> metadata
    ) {
        record(memory, eventType, score, metadata, memory.getSourceTaskRunId(), memory.getSourceMessageId());
    }

    public void record(
        UserMemory memory,
        MemoryEventType eventType,
        Double score,
        Map<String, Object> metadata,
        String taskRunId,
        String messageId
    ) {
        userMemoryEventRepository.save(UserMemoryEvent.builder()
            .memoryId(memory.getId())
            .userId(memory.getUserId())
            .eventType(eventType)
            .taskRunId(trimToNull(taskRunId))
            .messageId(trimToNull(messageId))
            .score(score)
            .metadata(normalizeMetadata(metadata))
            .build());
    }

    @Transactional(readOnly = true)
    public boolean existsEvent(
        UserMemory memory,
        MemoryEventType eventType,
        String taskRunId
    ) {
        String normalizedTaskRunId = trimToNull(taskRunId);
        if (normalizedTaskRunId == null) {
            return false;
        }
        return userMemoryEventRepository.existsByMemoryIdAndUserIdAndEventTypeAndTaskRunId(
            memory.getId(),
            memory.getUserId(),
            eventType,
            normalizedTaskRunId
        );
    }

    @Transactional(readOnly = true)
    public List<UserMemoryEvent> findEvents(Long userId, Long memoryId) {
        return userMemoryEventRepository.findByMemoryIdAndUserIdOrderByCreatedAtDesc(memoryId, userId);
    }

    private Map<String, Object> normalizeMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        return metadata;
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}
