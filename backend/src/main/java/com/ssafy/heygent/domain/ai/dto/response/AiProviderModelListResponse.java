package com.ssafy.heygent.domain.ai.dto.response;

import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AiProviderModelListResponse {

    private String defaultModel;
    private List<AiProviderModelItemResponse> providers;
}
