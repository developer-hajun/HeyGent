package com.ssafy.heygent.domain.memory.dto.request;

import java.time.LocalDateTime;
import java.util.Map;

import com.ssafy.heygent.domain.memory.entity.MemoryOperationType;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;

@Getter
public class CreateMemoryRequest {

    @NotNull(message = "기억 타입은 필수입니다.")
    private MemoryType memoryType;

    private MemoryStoreType storeType;

    private MemoryScopeType scopeType;

    private MemoryOperationType operationType;

    private Long targetMemoryId;

    @NotBlank(message = "기억 내용은 필수입니다.")
    @Size(max = 2000, message = "기억 내용은 2000자 이하여야 합니다.")
    private String content;

    @Size(max = 500, message = "기억 요약은 500자 이하여야 합니다.")
    private String summary;

    private Map<String, Object> metadata;

    @NotNull(message = "중요도는 필수입니다.")
    @DecimalMin(value = "0.0", message = "중요도는 0.0 이상이어야 합니다.")
    @DecimalMax(value = "1.0", message = "중요도는 1.0 이하여야 합니다.")
    private Double importance;

    @NotNull(message = "신뢰도는 필수입니다.")
    @DecimalMin(value = "0.0", message = "신뢰도는 0.0 이상이어야 합니다.")
    @DecimalMax(value = "1.0", message = "신뢰도는 1.0 이하여야 합니다.")
    private Double confidence;

    @Size(max = 100, message = "세션 키는 100자 이하여야 합니다.")
    private String sourceSessionKey;

    @Size(max = 100, message = "TaskRun ID는 100자 이하여야 합니다.")
    private String sourceTaskRunId;

    @Size(max = 100, message = "메시지 ID는 100자 이하여야 합니다.")
    private String sourceMessageId;

    @Size(max = 2000, message = "근거 내용은 2000자 이하여야 합니다.")
    private String evidence;

    @Size(max = 500, message = "갱신 사유는 500자 이하여야 합니다.")
    private String updateReason;

    private LocalDateTime validFrom;

    private LocalDateTime validUntil;

    private LocalDateTime expiresAt;
}
