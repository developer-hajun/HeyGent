package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiProviderStatusItemResponse {

    private String providerName;
    private String providerType;
    private String authType;
    private String displayName;
    private String description;
    private String connectType;
    private String defaultModel;
    private List<String> models;
    private boolean connected;
    private boolean available;
    private LocalDateTime expiresAt;
    private String status;
}
