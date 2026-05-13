package com.ssafy.heygent.domain.mattermost.service;

import java.net.URI;
import java.util.Map;

import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookRequest;
import com.ssafy.heygent.domain.mattermost.dto.MattermostWebhookResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@Service
public class MattermostService {

    private final RestTemplate restTemplate = new RestTemplate();

    public MattermostWebhookResponse sendWebhook(MattermostWebhookRequest request) {
        URI webhookUri = validateWebhookUrl(request.getWebhookUrl());
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            restTemplate.postForEntity(
                    webhookUri,
                    new HttpEntity<>(Map.of("text", request.getMessage().trim()), headers),
                    String.class
            );
            return MattermostWebhookResponse.builder()
                    .sent(true)
                    .build();
        } catch (RestClientException | IllegalArgumentException exception) {
            throw new CustomException(ErrorCode.MATTERMOST_REQUEST_FAILED);
        }
    }

    private URI validateWebhookUrl(String webhookUrl) {
        String trimmed = webhookUrl.trim();
        if (!trimmed.startsWith("https://") && !trimmed.startsWith("http://")) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        URI uri = URI.create(trimmed);
        if (uri.getHost() == null || !uri.getPath().startsWith("/hooks/")) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return uri;
    }
}
