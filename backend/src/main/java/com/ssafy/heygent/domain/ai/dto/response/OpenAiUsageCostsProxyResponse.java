package com.ssafy.heygent.domain.ai.dto.response;

import java.util.Map;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiUsageCostsProxyResponse {

    private String providerName;
    private Map<String, Object> usage;
    private Map<String, Object> costs;
}
