package com.ssafy.heygent.domain.ai.openai.dto;

import java.util.Map;

public record OpenAiUsage(
    long inputTokens,
    long cachedInputTokens,
    long outputTokens,
    long reasoningTokens,
    long totalTokens
) {

    public static OpenAiUsage empty() {
        return new OpenAiUsage(0, 0, 0, 0, 0);
    }

    public static OpenAiUsage from(Map<String, Object> usage) {
        if (usage == null || usage.isEmpty()) {
            return empty();
        }

        Map<String, Object> inputDetails = valueAsMap(usage.get("input_tokens_details"));
        Map<String, Object> outputDetails = valueAsMap(usage.get("output_tokens_details"));

        return new OpenAiUsage(
            valueAsLong(usage.get("input_tokens")),
            valueAsLong(inputDetails.get("cached_tokens")),
            valueAsLong(usage.get("output_tokens")),
            valueAsLong(outputDetails.get("reasoning_tokens")),
            valueAsLong(usage.get("total_tokens"))
        );
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> valueAsMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>)map;
        }
        return Map.of();
    }

    private static long valueAsLong(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value instanceof String text && !text.isBlank()) {
            return Long.parseLong(text);
        }
        return 0;
    }
}
