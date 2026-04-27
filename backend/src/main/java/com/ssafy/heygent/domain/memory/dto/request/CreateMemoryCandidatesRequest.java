package com.ssafy.heygent.domain.memory.dto.request;

import java.util.List;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import lombok.Getter;

@Getter
public class CreateMemoryCandidatesRequest {

    @Valid
    @NotEmpty(message = "기억 후보는 1개 이상이어야 합니다.")
    @Size(max = 20, message = "기억 후보는 한 번에 20개 이하로 전달해야 합니다.")
    private List<CreateMemoryRequest> candidates;
}
