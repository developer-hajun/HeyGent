package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiCodexOAuthStatusResponse {

    private String providerName;
    private boolean connected;
    private boolean available;
    private String status;
    private String accountId;
    private LocalDateTime expiresAt;
}
