package com.ssafy.heygent.domain.ai.dto.request;

import java.math.BigDecimal;
import java.util.Map;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class AiCommandUsageRecordRequest {

    @NotNull(message = "사용자 ID는 필수입니다.")
    private Long userId;

    @NotBlank(message = "provider 이름은 필수입니다.")
    private String providerName;

    @NotBlank(message = "모델 이름은 필수입니다.")
    private String model;

    @NotBlank(message = "TaskRun ID는 필수입니다.")
    private String taskRunId;

    private String stepRunId;

    private String sessionId;

    private String requestId;

    @Min(value = 0, message = "입력 토큰 수는 0 이상이어야 합니다.")
    private Long inputTokens;

    @Min(value = 0, message = "출력 토큰 수는 0 이상이어야 합니다.")
    private Long outputTokens;

    @Min(value = 0, message = "전체 토큰 수는 0 이상이어야 합니다.")
    private Long totalTokens;

    @Min(value = 0, message = "캐시 입력 토큰 수는 0 이상이어야 합니다.")
    private Long cachedInputTokens;

    @Min(value = 0, message = "reasoning 토큰 수는 0 이상이어야 합니다.")
    private Long reasoningTokens;

    @DecimalMin(value = "0.0", message = "예상 비용은 0 이상이어야 합니다.")
    private BigDecimal estimatedCostUsd;

    private Map<String, Object> metadata;
}
