package com.ssafy.heygent.domain.ai.openai.dto;

import java.util.List;
import java.util.Map;

public record OpenAiResponsesCommand(
    Long userId,
    String taskRunId,
    String stepRunId,
    String providerName,
    String model,
    List<Map<String, Object>> input,
    List<Map<String, Object>> tools,
    Object toolChoice,
    Map<String, Object> metadata
) {
}
