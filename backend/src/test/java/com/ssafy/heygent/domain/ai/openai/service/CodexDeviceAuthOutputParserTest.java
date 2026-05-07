package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class CodexDeviceAuthOutputParserTest {

    @Test
    void parseDeviceAuthOutput() {
        String output = """
            Follow these steps to sign in with ChatGPT using device code authorization:

            1. Open this link in your browser and sign in to your account
               https://auth.openai.com/codex/device

            2. Enter this one-time code
               NQ8T-KWD9X
            """;

        CodexDeviceAuthOutputParser.ParsedDeviceAuthOutput parsed =
            CodexDeviceAuthOutputParser.parse(output);

        assertThat(parsed.verificationUri()).isEqualTo("https://auth.openai.com/codex/device");
        assertThat(parsed.userCode()).isEqualTo("NQ8T-KWD9X");
        assertThat(parsed.isComplete()).isTrue();
    }

    @Test
    void parseAnsiColoredDeviceAuthOutput() {
        String output = """
            Open this link:
              \u001B[94mhttps://auth.openai.com/codex/device\u001B[0m

            Enter code:
              \u001B[94mABCD-EFGH\u001B[0m
            """;

        CodexDeviceAuthOutputParser.ParsedDeviceAuthOutput parsed =
            CodexDeviceAuthOutputParser.parse(output);

        assertThat(parsed.verificationUri()).isEqualTo("https://auth.openai.com/codex/device");
        assertThat(parsed.userCode()).isEqualTo("ABCD-EFGH");
        assertThat(parsed.isComplete()).isTrue();
    }
}
