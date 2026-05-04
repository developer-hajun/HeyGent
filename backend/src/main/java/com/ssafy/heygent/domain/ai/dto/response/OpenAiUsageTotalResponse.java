package com.ssafy.heygent.domain.ai.dto.response;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiUsageTotalResponse {

    private long requestCount;
    private long inputTokens;
    private long cachedInputTokens;
    private long outputTokens;
    private long reasoningTokens;
    private long totalTokens;
}
