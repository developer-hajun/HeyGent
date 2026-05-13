package com.ssafy.heygent.domain.mattermost.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class MattermostWebhookRequest {

    @NotBlank
    private String webhookUrl;

    @NotBlank
    private String message;
}
