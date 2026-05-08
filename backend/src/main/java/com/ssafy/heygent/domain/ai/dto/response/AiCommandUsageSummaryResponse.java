package com.ssafy.heygent.domain.ai.dto.response;

import java.math.BigDecimal;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AiCommandUsageSummaryResponse {

    private Long inputTokens;
    private Long outputTokens;
    private Long totalTokens;
    private Long cachedInputTokens;
    private Long reasoningTokens;
    private BigDecimal estimatedCostUsd;
    private String currency;
    private Integer recordCount;
}
