package com.ssafy.heygent.domain.mattermost.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record MattermostMessageRequest(
        @Size(max = 40)
        String target,

        @NotBlank
        @Size(max = 4000)
        String message
) {
}
