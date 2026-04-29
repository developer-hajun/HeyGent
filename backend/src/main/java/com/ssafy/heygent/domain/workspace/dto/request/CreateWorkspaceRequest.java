package com.ssafy.heygent.domain.workspace.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateWorkspaceRequest {

    @NotBlank(message = "워크스페이스 이름은 필수입니다.")
    @Size(max = 100, message = "워크스페이스 이름은 100자 이하여야 합니다.")
    private String name;

    @Size(max = 100, message = "Workspace Key는 100자 이하여야 합니다.")
    @Pattern(
        regexp = "^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
        message = "Workspace Key는 영문, 숫자, 하이픈, 언더스코어만 사용할 수 있습니다."
    )
    private String workspaceKey;
}
