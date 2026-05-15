package com.ssafy.heygent.domain.ai.dto.response;

import java.util.List;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AiCommandUsageListResponse {

    private AiCommandUsageSummaryResponse summary;
    private List<AiCommandUsageRecordResponse> records;
}
