package com.ssafy.heygent.domain.session.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.session.dto.request.CreateProductSessionRequest;
import com.ssafy.heygent.domain.session.dto.response.ProductSessionResponse;
import com.ssafy.heygent.domain.session.entity.ProductSession;
import com.ssafy.heygent.domain.session.entity.ProductSessionStatus;
import com.ssafy.heygent.domain.session.repository.ProductSessionRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductSessionService {

    private static final String DEFAULT_SESSION_TITLE = "새 AI 세션";

    private final ProductSessionRepository productSessionRepository;
    private final WorkspaceAccessService workspaceAccessService;

    @Transactional
    public ProductSessionResponse create(Long userId, CreateProductSessionRequest request) {
        ProductSession session = ProductSession.builder()
            .userId(userId)
            .title(resolveTitle(request.getTitle()))
            .workspaceKey(resolveWorkspaceKey(userId, request.getWorkspaceKey()))
            .status(ProductSessionStatus.ACTIVE)
            .build();

        return ProductSessionResponse.from(productSessionRepository.save(session));
    }

    public List<ProductSessionResponse> getMySessions(Long userId) {
        return productSessionRepository.findByUserIdOrderByUpdatedAtDescCreatedAtDesc(userId).stream()
            .map(ProductSessionResponse::from)
            .toList();
    }

    public ProductSessionResponse getSession(Long userId, Long sessionId) {
        return ProductSessionResponse.from(findOwnedSession(userId, sessionId));
    }

    public ProductSession findOwnedSession(Long userId, Long sessionId) {
        if (sessionId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        return productSessionRepository.findByIdAndUserId(sessionId, userId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }

    private String resolveTitle(String title) {
        String normalizedTitle = trimToNull(title);
        if (normalizedTitle == null) {
            return DEFAULT_SESSION_TITLE;
        }
        return normalizedTitle;
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }

    private String resolveWorkspaceKey(Long userId, String workspaceKey) {
        if (!StringUtils.hasText(workspaceKey)) {
            return null;
        }
        return workspaceAccessService.validateAccess(userId, workspaceKey);
    }
}
