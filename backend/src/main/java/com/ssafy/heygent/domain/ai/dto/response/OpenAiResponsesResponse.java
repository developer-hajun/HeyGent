package com.ssafy.heygent.domain.ai.dto.response;

import java.util.List;
import java.util.Map;

import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiResponsesResponse {

    private String providerName;
    private String authType;
    private String model;
    private String responseId;
    private String outputText;
    private List<Map<String, Object>> toolCalls;
    private String finishReason;
    private OpenAiUsageResponse usage;

    public static OpenAiResponsesResponse from(OpenAiResponsesResult result) {
        return OpenAiResponsesResponse.builder()
            .providerName(result.providerName())
            .authType(result.authType())
            .model(result.model())
            .responseId(result.responseId())
            .outputText(result.outputText())
            .toolCalls(result.toolCalls())
            .finishReason(result.finishReason())
            .usage(OpenAiUsageResponse.from(result.usage()))
            .build();
    }
}
