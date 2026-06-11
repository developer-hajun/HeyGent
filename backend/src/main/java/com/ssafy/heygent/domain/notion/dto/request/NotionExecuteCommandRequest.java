package com.ssafy.heygent.domain.notion.dto.request;

import java.util.Map;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class NotionExecuteCommandRequest {

    @NotBlank
    private String method;

    @NotBlank
    private String endpoint;

    private String notionVersion;

    private Map<String, Object> params;
}
