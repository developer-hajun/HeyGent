package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiApiKeyConnectionResponse {

    private String providerName;
    private boolean connected;
    private String status;
    private LocalDateTime updatedAt;
}
