package com.ssafy.heygent.domain.mattermost.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record MattermostChannelCreateRequest(
        @NotBlank
        @Size(max = 40)
        @Pattern(regexp = "^[\\p{L}\\p{N}_-]+$")
        String alias,

        @Size(max = 60)
        String displayName,

        @NotBlank
        @Size(max = 512)
        String webhookUrl,

        boolean defaultChannel
) {
}
