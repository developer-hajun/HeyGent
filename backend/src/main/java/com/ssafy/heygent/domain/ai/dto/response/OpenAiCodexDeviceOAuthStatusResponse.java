package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiCodexDeviceOAuthStatusResponse {

    private String providerName;
    private String state;
    private boolean connected;
    private boolean available;
    private String status;
    private String accountId;
    private LocalDateTime expiresAt;
    private String message;
}
