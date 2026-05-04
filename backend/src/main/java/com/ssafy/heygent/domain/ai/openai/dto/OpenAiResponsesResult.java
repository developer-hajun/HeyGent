package com.ssafy.heygent.domain.ai.openai.dto;

import java.util.List;
import java.util.Map;

public record OpenAiResponsesResult(
    String providerName,
    String authType,
    String model,
    String responseId,
    String outputText,
    List<Map<String, Object>> toolCalls,
    String finishReason,
    OpenAiUsage usage,
    Map<String, Object> rawResponse
) {
}
