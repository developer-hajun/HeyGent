package com.ssafy.heygent.domain.ai.dto.response;

import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiUsageResponse {

    private long inputTokens;
    private long cachedInputTokens;
    private long outputTokens;
    private long reasoningTokens;
    private long totalTokens;

    public static OpenAiUsageResponse from(OpenAiUsage usage) {
        OpenAiUsage safeUsage = usage == null ? OpenAiUsage.empty() : usage;
        return OpenAiUsageResponse.builder()
            .inputTokens(safeUsage.inputTokens())
            .cachedInputTokens(safeUsage.cachedInputTokens())
            .outputTokens(safeUsage.outputTokens())
            .reasoningTokens(safeUsage.reasoningTokens())
            .totalTokens(safeUsage.totalTokens())
            .build();
    }
}
