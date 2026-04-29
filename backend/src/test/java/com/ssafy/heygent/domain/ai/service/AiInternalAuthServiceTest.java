package com.ssafy.heygent.domain.ai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.ai.dto.request.AiAuthValidateRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiAuthValidateResponse;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class AiInternalAuthServiceTest {

    private static final Long USER_ID = 1L;
    private static final String JWT_SECRET = "12345678901234567890123456789012";

    @Mock
    private UserRepository userRepository;

    @Mock
    private WorkspaceAccessService workspaceAccessService;

    private JwtProvider jwtProvider;
    private AiInternalAuthService aiInternalAuthService;

    @BeforeEach
    void setUp() {
        jwtProvider = new JwtProvider(JWT_SECRET);
        aiInternalAuthService = new AiInternalAuthService(jwtProvider, userRepository, workspaceAccessService);
    }

    @Test
    void validateReturnsVerifiedUserContext() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);
        AiAuthValidateRequest request = request(accessToken, " backend-project ");
        LocalDateTime beforeValidate = LocalDateTime.now();

        when(userRepository.existsById(USER_ID)).thenReturn(true);
        when(workspaceAccessService.validateAccess(USER_ID, " backend-project ")).thenReturn("backend-project");

        AiAuthValidateResponse response = aiInternalAuthService.validate(request);

        assertThat(response.getUserId()).isEqualTo(USER_ID);
        assertThat(response.getWorkspaceKey()).isEqualTo("backend-project");
        assertThat(response.getScope()).containsExactly("AI_TASK_RUN");
        assertThat(response.getJwtExpiresAt()).isAfter(beforeValidate);
        assertThat(response.getScopeExpiresAt()).isAfter(beforeValidate);
    }

    @Test
    void validateFailsWhenAccessTokenIsInvalid() {
        AiAuthValidateRequest request = request("invalid-token", null);

        assertThatThrownBy(() -> aiInternalAuthService.validate(request))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.INVALID_TOKEN);
    }

    @Test
    void validateFailsWhenUserDoesNotExist() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);
        AiAuthValidateRequest request = request(accessToken, null);

        when(userRepository.existsById(USER_ID)).thenReturn(false);

        assertThatThrownBy(() -> aiInternalAuthService.validate(request))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.INVALID_TOKEN);
    }

    private AiAuthValidateRequest request(String accessToken, String workspaceKey) {
        AiAuthValidateRequest request = new AiAuthValidateRequest();
        ReflectionTestUtils.setField(request, "accessToken", accessToken);
        ReflectionTestUtils.setField(request, "workspaceKey", workspaceKey);
        return request;
    }
}
