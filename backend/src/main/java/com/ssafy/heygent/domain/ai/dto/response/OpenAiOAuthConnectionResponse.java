package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiOAuthConnectionResponse {

    private String providerName;
    private boolean connected;
    private String status;
    private List<String> scopes;
    private LocalDateTime expiresAt;
}
