package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AiAuthValidateResponse {

    private Long userId;
    private String workspaceKey;
    private List<String> scope;
    private LocalDateTime jwtExpiresAt;
    private LocalDateTime scopeExpiresAt;
}
