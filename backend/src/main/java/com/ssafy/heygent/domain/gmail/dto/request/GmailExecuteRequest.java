package com.ssafy.heygent.domain.gmail.dto.request;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class GmailExecuteRequest {

    @NotNull
    private Long userId;

    @Valid
    @NotEmpty
    private List<GmailExecuteCommandRequest> commands;
}
