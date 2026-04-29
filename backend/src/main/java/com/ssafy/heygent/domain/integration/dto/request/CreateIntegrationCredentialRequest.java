package com.ssafy.heygent.domain.integration.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateIntegrationCredentialRequest {

    @NotBlank(message = "Credential Key는 필수입니다.")
    @Size(max = 100, message = "Credential Key는 100자 이하여야 합니다.")
    private String credentialKey;

    @NotBlank(message = "Secret 값은 필수입니다.")
    @Size(max = 4000, message = "Secret 값은 4000자 이하여야 합니다.")
    private String secretValue;
}
