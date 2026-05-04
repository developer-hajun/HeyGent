package com.ssafy.heygent.domain.ai.service;

import java.util.List;
import java.util.Map;

import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiResponsesRequest;

public final class TestOpenAiResponsesRequestFactory {

    private TestOpenAiResponsesRequestFactory() {
    }

    public static OpenAiResponsesRequest create(
        Long userId,
        String taskRunId,
        String stepRunId,
        String providerName,
        String model
    ) {
        OpenAiResponsesRequest request = new OpenAiResponsesRequest();
        ReflectionTestUtils.setField(request, "userId", userId);
        ReflectionTestUtils.setField(request, "taskRunId", taskRunId);
        ReflectionTestUtils.setField(request, "stepRunId", stepRunId);
        ReflectionTestUtils.setField(request, "providerName", providerName);
        ReflectionTestUtils.setField(request, "model", model);
        ReflectionTestUtils.setField(request, "input", List.of(Map.of("role", "user", "content", "hello")));
        ReflectionTestUtils.setField(request, "tools", List.of());
        ReflectionTestUtils.setField(request, "metadata", Map.of("sessionKey", "workspace-a"));
        return request;
    }
}
