package com.ssafy.heygent.domain.gmail.dto.request;

import java.util.Map;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class GmailExecuteCommandRequest {

    @NotBlank
    private String method;

    @NotBlank
    private String endpoint;

    private Map<String, Object> params;
}
