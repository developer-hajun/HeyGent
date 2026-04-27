package com.ssafy.heygent.domain.memory.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class UserMemoryResponse {

    private Long id;
    private MemoryType memoryType;
    private String content;
    private String summary;
    private Double importance;
    private Double confidence;
    private MemoryStatus status;
    private String sourceSessionKey;
    private String sourceTaskRunId;
    private LocalDateTime lastAccessedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static UserMemoryResponse from(UserMemory memory) {
        return UserMemoryResponse.builder()
            .id(memory.getId())
            .memoryType(memory.getMemoryType())
            .content(memory.getContent())
            .summary(memory.getSummary())
            .importance(memory.getImportance())
            .confidence(memory.getConfidence())
            .status(memory.getStatus())
            .sourceSessionKey(memory.getSourceSessionKey())
            .sourceTaskRunId(memory.getSourceTaskRunId())
            .lastAccessedAt(memory.getLastAccessedAt())
            .createdAt(memory.getCreatedAt())
            .updatedAt(memory.getUpdatedAt())
            .build();
    }
}
