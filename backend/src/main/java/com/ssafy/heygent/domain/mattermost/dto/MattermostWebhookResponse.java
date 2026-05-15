package com.ssafy.heygent.domain.mattermost.dto;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class MattermostWebhookResponse {

    private boolean sent;
}
