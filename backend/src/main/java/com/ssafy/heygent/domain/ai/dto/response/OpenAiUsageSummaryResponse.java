package com.ssafy.heygent.domain.ai.dto.response;

import java.time.LocalDate;
import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class OpenAiUsageSummaryResponse {

    private LocalDate from;
    private LocalDate to;
    private OpenAiUsageTotalResponse total;
    private List<OpenAiUsageDailyResponse> items;
}
