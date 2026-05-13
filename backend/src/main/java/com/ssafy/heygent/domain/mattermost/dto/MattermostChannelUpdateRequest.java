package com.ssafy.heygent.domain.mattermost.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record MattermostChannelUpdateRequest(
        @NotBlank
        @Size(max = 40)
        @Pattern(regexp = "^[A-Za-z0-9_-]+$")
        String alias,

        @NotBlank
        @Size(max = 60)
        String displayName,

        @Size(max = 512)
        String webhookUrl,

        boolean defaultChannel
) {
}
