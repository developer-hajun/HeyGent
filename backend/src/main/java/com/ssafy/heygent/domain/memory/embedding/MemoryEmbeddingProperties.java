package com.ssafy.heygent.domain.memory.embedding;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "memory.embedding")
public class MemoryEmbeddingProperties {

    private boolean enabled = true;
    private String baseUrl = "https://api.openai.com/v1";
    private String apiKey;
    private String model = "text-embedding-3-small";
    private int dimensions = 1536;
    private int timeoutSeconds = 10;
}
