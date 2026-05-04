package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDate;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiUsageDailyResponse {

    private LocalDate date;
    private long requestCount;
    private long inputTokens;
    private long cachedInputTokens;
    private long outputTokens;
    private long reasoningTokens;
    private long totalTokens;
}
