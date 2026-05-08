package com.ssafy.heygent.domain.ai.openai.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public record OpenAiOAuthTokenPayload(
    String accessToken,
    String refreshToken,
    String tokenType,
    List<String> scopes,
    LocalDateTime expiresAt,
    Map<String, Object> rawPayload
) {
}
