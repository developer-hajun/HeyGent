package com.ssafy.heygent.domain.ai.dto.request;

import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class OpenAiCodexOAuthCompleteRequest {

    private String redirectUrl;
    private String code;
    private String state;
}
