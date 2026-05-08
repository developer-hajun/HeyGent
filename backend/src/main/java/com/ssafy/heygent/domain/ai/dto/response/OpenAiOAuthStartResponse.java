package com.ssafy.heygent.domain.ai.dto.response;

import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiOAuthStartResponse {

    private String status;
    private String authorizationUrl;
    private String state;
    private String redirectUri;
    private List<String> scopes;
}
