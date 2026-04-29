package com.ssafy.heygent.domain.session.dto.request;

import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateProductSessionRequest {

    @Size(max = 100, message = "세션 제목은 100자 이하여야 합니다.")
    private String title;

    @Size(max = 100, message = "Workspace Key는 100자 이하여야 합니다.")
    private String workspaceKey;
}
