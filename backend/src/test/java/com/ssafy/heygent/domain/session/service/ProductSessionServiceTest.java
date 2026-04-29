package com.ssafy.heygent.domain.session.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.session.dto.request.CreateProductSessionRequest;
import com.ssafy.heygent.domain.session.dto.response.ProductSessionResponse;
import com.ssafy.heygent.domain.session.entity.ProductSession;
import com.ssafy.heygent.domain.session.entity.ProductSessionStatus;
import com.ssafy.heygent.domain.session.repository.ProductSessionRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class ProductSessionServiceTest {

    private static final Long USER_ID = 1L;
    private static final Long OTHER_USER_ID = 2L;

    @Mock
    private ProductSessionRepository productSessionRepository;

    @InjectMocks
    private ProductSessionService productSessionService;

    @Test
    void createSavesProductSessionForUser() {
        CreateProductSessionRequest request = request(" 회의 정리 ", " backend-project ");
        ProductSession savedSession = session(10L, USER_ID, "회의 정리", "backend-project");

        when(productSessionRepository.save(any(ProductSession.class))).thenReturn(savedSession);

        ProductSessionResponse response = productSessionService.create(USER_ID, request);

        ArgumentCaptor<ProductSession> captor = ArgumentCaptor.forClass(ProductSession.class);
        verify(productSessionRepository).save(captor.capture());
        ProductSession capturedSession = captor.getValue();

        assertThat(capturedSession.getUserId()).isEqualTo(USER_ID);
        assertThat(capturedSession.getTitle()).isEqualTo("회의 정리");
        assertThat(capturedSession.getWorkspaceKey()).isEqualTo("backend-project");
        assertThat(capturedSession.getStatus()).isEqualTo(ProductSessionStatus.ACTIVE);
        assertThat(response.getSessionId()).isEqualTo(10L);
    }

    @Test
    void createUsesDefaultTitleWhenTitleIsBlank() {
        CreateProductSessionRequest request = request(" ", null);
        ProductSession savedSession = session(11L, USER_ID, "새 AI 세션", null);

        when(productSessionRepository.save(any(ProductSession.class))).thenReturn(savedSession);

        ProductSessionResponse response = productSessionService.create(USER_ID, request);

        assertThat(response.getTitle()).isEqualTo("새 AI 세션");
    }

    @Test
    void getMySessionsReturnsOwnedSessions() {
        ProductSession session = session(12L, USER_ID, "회의 정리", "backend-project");
        when(productSessionRepository.findByUserIdOrderByUpdatedAtDescCreatedAtDesc(USER_ID))
            .thenReturn(List.of(session));

        List<ProductSessionResponse> responses = productSessionService.getMySessions(USER_ID);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getSessionId()).isEqualTo(12L);
    }

    @Test
    void getSessionReturnsOwnedSession() {
        ProductSession session = session(13L, USER_ID, "회의 정리", "backend-project");
        when(productSessionRepository.findByIdAndUserId(13L, USER_ID)).thenReturn(Optional.of(session));

        ProductSessionResponse response = productSessionService.getSession(USER_ID, 13L);

        assertThat(response.getSessionId()).isEqualTo(13L);
        assertThat(response.getUserId()).isEqualTo(USER_ID);
    }

    @Test
    void getSessionFailsWhenSessionIsNotOwnedByUser() {
        when(productSessionRepository.findByIdAndUserId(14L, OTHER_USER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> productSessionService.getSession(OTHER_USER_ID, 14L))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    private CreateProductSessionRequest request(String title, String workspaceKey) {
        CreateProductSessionRequest request = new CreateProductSessionRequest();
        ReflectionTestUtils.setField(request, "title", title);
        ReflectionTestUtils.setField(request, "workspaceKey", workspaceKey);
        return request;
    }

    private ProductSession session(Long id, Long userId, String title, String workspaceKey) {
        return ProductSession.builder()
            .id(id)
            .userId(userId)
            .title(title)
            .workspaceKey(workspaceKey)
            .status(ProductSessionStatus.ACTIVE)
            .build();
    }
}
