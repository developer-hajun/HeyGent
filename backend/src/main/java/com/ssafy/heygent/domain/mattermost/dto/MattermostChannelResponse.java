package com.ssafy.heygent.domain.mattermost.dto;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.mattermost.entity.MattermostChannel;

public record MattermostChannelResponse(
        Long id,
        String alias,
        String displayName,
        boolean defaultChannel,
        boolean webhookConfigured,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {

    public static MattermostChannelResponse from(MattermostChannel channel) {
        return new MattermostChannelResponse(
                channel.getId(),
                channel.getAlias(),
                channel.getDisplayName(),
                channel.isDefaultChannel(),
                channel.getWebhookUrl() != null && !channel.getWebhookUrl().isBlank(),
                channel.getCreatedAt(),
                channel.getUpdatedAt()
        );
    }
}
