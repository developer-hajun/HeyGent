package com.ssafy.heygent.domain.ai.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class AiAuthValidateRequest {

    @NotBlank(message = "Access Token은 필수입니다.")
    private String accessToken;

    private String workspaceKey;
}
