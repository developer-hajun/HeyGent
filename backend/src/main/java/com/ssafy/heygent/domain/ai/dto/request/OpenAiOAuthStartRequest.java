package com.ssafy.heygent.domain.ai.dto.request;

import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class OpenAiOAuthStartRequest {

    private String redirectUri;
    private boolean force;
}
