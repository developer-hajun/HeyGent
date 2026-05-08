package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiCredentialIssueResponse {

    private String providerName;
    private String authType;
    private String model;
    private String credentialType;
    private String credential;
    private LocalDateTime expiresAt;
}
