package com.ssafy.heygent.domain.ai.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class OpenAiCredentialIssueRequest {

    @NotNull(message = "사용자 ID는 필수입니다.")
    private Long userId;

    @NotBlank(message = "OpenAI Provider는 필수입니다.")
    private String providerName;

    @NotBlank(message = "OpenAI model은 필수입니다.")
    private String model;
}
