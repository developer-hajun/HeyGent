package com.ssafy.heygent.domain.integration.dto.request;

import com.ssafy.heygent.domain.integration.entity.IntegrationProvider;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateIntegrationRequest {

    @NotBlank(message = "Integration 이름은 필수입니다.")
    @Size(max = 100, message = "Integration 이름은 100자 이하여야 합니다.")
    private String name;

    @NotNull(message = "Provider는 필수입니다.")
    private IntegrationProvider provider;

    @Size(max = 100, message = "Workspace Key는 100자 이하여야 합니다.")
    private String workspaceKey;
}
