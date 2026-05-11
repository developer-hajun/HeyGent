package com.ssafy.heygent.domain.memory.dto.response;

import java.time.LocalDateTime;
import java.util.Map;

import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.entity.UserMemoryEvent;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class UserMemoryEventResponse {

    private Long id;
    private Long memoryId;
    private MemoryEventType eventType;
    private String requestId;
    private String taskRunId;
    private String messageId;
    private Double score;
    private Map<String, Object> metadata;
    private LocalDateTime createdAt;

    public static UserMemoryEventResponse from(UserMemoryEvent event) {
        return UserMemoryEventResponse.builder()
            .id(event.getId())
            .memoryId(event.getMemoryId())
            .eventType(event.getEventType())
            .requestId(event.getRequestId())
            .taskRunId(event.getTaskRunId())
            .messageId(event.getMessageId())
            .score(event.getScore())
            .metadata(event.getMetadata())
            .createdAt(event.getCreatedAt())
            .build();
    }
}
