package com.ssafy.heygent.domain.notion.dto.request;

import java.util.Map;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class NotionExecuteRequest {

    @NotBlank
    private String action;        // 수행할 액션 (예: create_page, query_database 등)

    private String targetId;      // 페이지ID, DB ID 등 (액션에 따라 사용)

    private Map<String, Object> params; // 액션별 파라미터
}
