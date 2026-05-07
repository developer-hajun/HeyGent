package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiCodexDeviceOAuthStartResponse {

    private String providerName;
    private String state;
    private String status;
    private String verificationUri;
    private String userCode;
    private LocalDateTime expiresAt;
    private String message;
}
