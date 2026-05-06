package com.ssafy.heygent.domain.ai.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class OpenAiApiKeyUpsertRequest {

    @NotBlank(message = "OpenAI API Key는 필수입니다.")
    private String apiKey;
}
