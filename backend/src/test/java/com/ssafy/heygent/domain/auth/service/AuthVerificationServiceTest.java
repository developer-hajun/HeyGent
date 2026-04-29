package com.ssafy.heygent.domain.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatExceptionOfType;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.ssafy.heygent.domain.auth.dto.response.AuthVerificationResponse;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class AuthVerificationServiceTest {

    private static final String JWT_SECRET = "12345678901234567890123456789012";
    private static final String INTERNAL_SERVICE_TOKEN = "internal-service-token";
    private static final Long USER_ID = 1L;

    @Mock
    private UserRepository userRepository;

    private AuthVerificationService authVerificationService;
    private JwtProvider jwtProvider;

    @BeforeEach
    void setUp() {
        jwtProvider = new JwtProvider(JWT_SECRET);
        authVerificationService = new AuthVerificationService(
            userRepository,
            jwtProvider,
            INTERNAL_SERVICE_TOKEN
        );
    }

    @Test
    void verifyReturnsUserInfoWhenInternalTokenAndAccessTokenAreValid() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);
        Instant beforeVerification = Instant.now();

        when(userRepository.findById(USER_ID)).thenReturn(Optional.of(user()));

        AuthVerificationResponse response = authVerificationService.verify(
            INTERNAL_SERVICE_TOKEN,
            accessToken
        );

        assertThat(response.getUserId()).isEqualTo(USER_ID);
        assertThat(response.getWorkspaceKey()).isNull();
        assertThat(response.getScopes()).containsExactly("USER");
        assertThat(response.getTokenExpiresAt()).isAfter(beforeVerification);
    }

    @Test
    void verifyRejectsMissingInternalToken() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);

        assertThatExceptionOfType(CustomException.class)
            .isThrownBy(() -> authVerificationService.verify(null, accessToken))
            .satisfies(exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.ACCESS_DENIED));
        verify(userRepository, never()).findById(USER_ID);
    }

    @Test
    void verifyRejectsDifferentInternalToken() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);

        assertThatExceptionOfType(CustomException.class)
            .isThrownBy(() -> authVerificationService.verify("wrong-token", accessToken))
            .satisfies(exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.ACCESS_DENIED));
        verify(userRepository, never()).findById(USER_ID);
    }

    @Test
    void verifyRejectsInvalidAccessToken() {
        assertThatExceptionOfType(CustomException.class)
            .isThrownBy(() -> authVerificationService.verify(INTERNAL_SERVICE_TOKEN, "invalid-access-token"))
            .satisfies(exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.INVALID_TOKEN));
        verify(userRepository, never()).findById(USER_ID);
    }

    @Test
    void verifyRejectsTokenWhenSubjectUserDoesNotExist() {
        String accessToken = jwtProvider.createAccessToken(USER_ID);

        when(userRepository.findById(USER_ID)).thenReturn(Optional.empty());

        assertThatExceptionOfType(CustomException.class)
            .isThrownBy(() -> authVerificationService.verify(INTERNAL_SERVICE_TOKEN, accessToken))
            .satisfies(exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.INVALID_TOKEN));
    }

    private User user() {
        return User.builder()
            .id(USER_ID)
            .kakaoId(100L)
            .nickname("테스트 사용자")
            .profileImage("https://example.com/profile.png")
            .build();
    }
}
