package com.ssafy.heygent.domain.notion.dto.request;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class NotionExecuteRequest {

    @NotNull
    private Long userId;

    @Valid
    @NotEmpty
    private List<NotionExecuteCommandRequest> commands;
}
