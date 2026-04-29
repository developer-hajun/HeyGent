package com.ssafy.heygent.domain.session.dto.response;

import java.time.LocalDateTime;

import com.ssafy.heygent.domain.session.entity.ProductSession;
import com.ssafy.heygent.domain.session.entity.ProductSessionStatus;

import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class ProductSessionResponse {

    private Long sessionId;
    private Long userId;
    private String title;
    private String workspaceKey;
    private ProductSessionStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static ProductSessionResponse from(ProductSession session) {
        return ProductSessionResponse.builder()
            .sessionId(session.getId())
            .userId(session.getUserId())
            .title(session.getTitle())
            .workspaceKey(session.getWorkspaceKey())
            .status(session.getStatus())
            .createdAt(session.getCreatedAt())
            .updatedAt(session.getUpdatedAt())
            .build();
    }
}
