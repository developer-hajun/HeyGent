package com.ssafy.heygent.domain.memory.dto.response;

import java.time.LocalDateTime;
import java.util.Map;

import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class UserMemoryResponse {

    private Long id;
    private MemoryStoreType storeType;
    private MemoryType memoryType;
    private MemoryScopeType scopeType;
    private String content;
    private String summary;
    private Map<String, Object> metadata;
    private Double importance;
    private Double confidence;
    private MemoryStatus status;
    private String sourceSessionKey;
    private String sourceTaskRunId;
    private String sourceMessageId;
    private String evidence;
    private String updateReason;
    private Long supersededByMemoryId;
    private LocalDateTime validFrom;
    private LocalDateTime validUntil;
    private LocalDateTime invalidatedAt;
    private LocalDateTime expiresAt;
    private Long accessCount;
    private Long usedCount;
    private LocalDateTime lastUsedAt;
    private Double usefulnessScore;
    private LocalDateTime lastAccessedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static UserMemoryResponse from(UserMemory memory) {
        return UserMemoryResponse.builder()
            .id(memory.getId())
            .storeType(memory.getStoreType())
            .memoryType(memory.getMemoryType())
            .scopeType(memory.getScopeType())
            .content(memory.getContent())
            .summary(memory.getSummary())
            .metadata(memory.getMetadata())
            .importance(memory.getImportance())
            .confidence(memory.getConfidence())
            .status(memory.getStatus())
            .sourceSessionKey(memory.getSourceSessionKey())
            .sourceTaskRunId(memory.getSourceTaskRunId())
            .sourceMessageId(memory.getSourceMessageId())
            .evidence(memory.getEvidence())
            .updateReason(memory.getUpdateReason())
            .supersededByMemoryId(memory.getSupersededByMemoryId())
            .validFrom(memory.getValidFrom())
            .validUntil(memory.getValidUntil())
            .invalidatedAt(memory.getInvalidatedAt())
            .expiresAt(memory.getExpiresAt())
            .accessCount(memory.getAccessCount())
            .usedCount(memory.getUsedCount())
            .lastUsedAt(memory.getLastUsedAt())
            .usefulnessScore(memory.getUsefulnessScore())
            .lastAccessedAt(memory.getLastAccessedAt())
            .createdAt(memory.getCreatedAt())
            .updatedAt(memory.getUpdatedAt())
            .build();
    }
}
