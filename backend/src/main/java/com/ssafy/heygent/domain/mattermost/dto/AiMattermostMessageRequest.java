package com.ssafy.heygent.domain.mattermost.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class AiMattermostMessageRequest {

    @NotNull
    private Long userId;

    @Size(max = 40)
    private String target;

    @NotBlank
    @Size(max = 4000)
    private String message;

    public MattermostMessageRequest toMessageRequest() {
        return new MattermostMessageRequest(target, message);
    }
}
