package com.ssafy.heygent.domain.ai.openai.dto;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;

import org.junit.jupiter.api.Test;

class OpenAiUsageTest {

    @Test
    void fromParsesResponsesUsageFields() {
        OpenAiUsage usage = OpenAiUsage.from(Map.of(
            "input_tokens", 100,
            "input_tokens_details", Map.of("cached_tokens", 20),
            "output_tokens", 40,
            "output_tokens_details", Map.of("reasoning_tokens", 10),
            "total_tokens", 140
        ));

        assertThat(usage.inputTokens()).isEqualTo(100);
        assertThat(usage.cachedInputTokens()).isEqualTo(20);
        assertThat(usage.outputTokens()).isEqualTo(40);
        assertThat(usage.reasoningTokens()).isEqualTo(10);
        assertThat(usage.totalTokens()).isEqualTo(140);
    }

    @Test
    void fromReturnsEmptyUsageWhenMissing() {
        OpenAiUsage usage = OpenAiUsage.from(Map.of());

        assertThat(usage).isEqualTo(OpenAiUsage.empty());
    }
}
