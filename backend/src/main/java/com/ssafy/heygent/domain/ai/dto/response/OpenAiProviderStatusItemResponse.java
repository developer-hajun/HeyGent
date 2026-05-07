package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiProviderStatusItemResponse {

    private String providerName;
    private String providerType;
    private String authType;
    private String defaultModel;
    private boolean connected;
    private boolean available;
    private LocalDateTime expiresAt;
    private String status;
}
