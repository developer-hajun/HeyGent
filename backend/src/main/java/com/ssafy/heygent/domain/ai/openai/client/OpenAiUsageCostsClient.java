package com.ssafy.heygent.domain.ai.openai.client;

import java.time.Duration;
import java.util.Map;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OpenAiUsageCostsClient {

    private static final String USAGE_PATH = "/organization/usage/completions";
    private static final String COSTS_PATH = "/organization/costs";
    private static final String DEFAULT_BUCKET_WIDTH = "1d";

    private final OpenAiProperties properties;

    public Map<String, Object> getUsage(String credential, long startTime, Long endTime) {
        return get(credential, USAGE_PATH, startTime, endTime);
    }

    public Map<String, Object> getCosts(String credential, long startTime, Long endTime) {
        return get(credential, COSTS_PATH, startTime, endTime);
    }

    private Map<String, Object> get(String credential, String path, long startTime, Long endTime) {
        try {
            Map<String, Object> response = restClient(credential).get()
                .uri(uriBuilder -> {
                    uriBuilder.path(path)
                        .queryParam("start_time", startTime)
                        .queryParam("bucket_width", DEFAULT_BUCKET_WIDTH);
                    if (endTime != null) {
                        uriBuilder.queryParam("end_time", endTime);
                    }
                    return uriBuilder.build();
                })
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });
            return response == null ? Map.of() : response;
        } catch (RestClientException exception) {
            log.warn("Failed to query OpenAI usage API. path={}", path, exception);
            throw new CustomException(ErrorCode.OPENAI_USAGE_QUERY_FAILED);
        }
    }

    private RestClient restClient(String credential) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));
        requestFactory.setReadTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));

        return RestClient.builder()
            .requestFactory(requestFactory)
            .baseUrl(properties.getUsageApiBaseUrl())
            .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + credential)
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .build();
    }
}
