package com.ssafy.heygent.domain.auth.dto.response;

import java.time.Instant;
import java.util.List;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
@AllArgsConstructor
public class AuthVerificationResponse {

    private Long userId;
    private String workspaceKey;
    private List<String> scopes;
    private Instant tokenExpiresAt;
}
