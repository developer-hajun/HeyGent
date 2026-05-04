package com.ssafy.heygent.domain.ai.dto.request;

import java.util.List;
import java.util.Map;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class OpenAiResponsesRequest {

    @NotNull(message = "사용자 ID는 필수입니다.")
    private Long userId;

    private String taskRunId;

    private String stepRunId;

    private String providerName;

    private String model;

    @NotEmpty(message = "OpenAI input은 필수입니다.")
    private List<Map<String, Object>> input;

    private List<Map<String, Object>> tools;

    private Object toolChoice;

    private Map<String, Object> metadata;
}
