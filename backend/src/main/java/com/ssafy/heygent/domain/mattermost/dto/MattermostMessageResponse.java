package com.ssafy.heygent.domain.mattermost.dto;

public record MattermostMessageResponse(
        boolean sent,
        String target,
        String displayName
) {
}
