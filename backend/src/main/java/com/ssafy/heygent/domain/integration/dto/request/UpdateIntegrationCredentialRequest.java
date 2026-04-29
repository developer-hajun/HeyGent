package com.ssafy.heygent.domain.integration.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class UpdateIntegrationCredentialRequest {

    @NotBlank(message = "Secret 값은 필수입니다.")
    @Size(max = 4000, message = "Secret 값은 4000자 이하여야 합니다.")
    private String secretValue;
}
