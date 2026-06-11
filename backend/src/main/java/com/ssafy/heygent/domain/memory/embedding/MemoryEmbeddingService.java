package com.ssafy.heygent.domain.memory.embedding;

import java.net.URI;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Random;

import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class MemoryEmbeddingService {

    private static final String EMBEDDINGS_PATH = "/embeddings";

    private final MemoryEmbeddingProperties properties;

    public List<Double> embed(String text) {
        if (!properties.isEnabled() || !StringUtils.hasText(properties.getApiKey())) {
            return createLocalEmbedding(text);
        }

        try {
            return createRemoteEmbedding(text);
        } catch (RuntimeException exception) {
            log.warn("Failed to create remote memory embedding. Use local fallback.", exception);
            return createLocalEmbedding(text);
        }
    }

    private List<Double> createRemoteEmbedding(String text) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));
        requestFactory.setReadTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));

        RestClient restClient = RestClient.builder()
            .requestFactory(requestFactory)
            .baseUrl(properties.getBaseUrl())
            .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getApiKey())
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();

        EmbeddingResponse response = restClient.post()
            .uri(URI.create(properties.getBaseUrl() + EMBEDDINGS_PATH))
            .body(Map.of(
                "model", properties.getModel(),
                "input", text,
                "dimensions", properties.getDimensions()
            ))
            .retrieve()
            .body(EmbeddingResponse.class);

        if (response == null || response.data() == null || response.data().isEmpty()) {
            return createLocalEmbedding(text);
        }
        return response.data().get(0).embedding();
    }

    private List<Double> createLocalEmbedding(String text) {
        Random random = new Random(text.hashCode());
        double[] values = new double[properties.getDimensions()];
        double norm = 0.0;

        for (int i = 0; i < values.length; i++) {
            values[i] = random.nextDouble(-1.0, 1.0);
            norm += values[i] * values[i];
        }

        double normalizedNorm = Math.sqrt(norm);
        return java.util.stream.DoubleStream.of(values)
            .map(value -> value / normalizedNorm)
            .boxed()
            .toList();
    }

    public int getDimensions() {
        return properties.getDimensions();
    }

    private record EmbeddingResponse(List<EmbeddingData> data) {
    }

    private record EmbeddingData(List<Double> embedding) {
    }
}
