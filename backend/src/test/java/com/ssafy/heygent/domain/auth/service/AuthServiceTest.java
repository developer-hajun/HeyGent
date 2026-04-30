package com.ssafy.heygent.domain.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Optional;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import com.ssafy.heygent.domain.auth.dto.response.TokenResponse;
import com.ssafy.heygent.domain.auth.oauth.KakaoOAuthService;
import com.ssafy.heygent.domain.auth.oauth.KakaoUserInfo;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    private static final String JWT_SECRET = "12345678901234567890123456789012";
    private static final String KAKAO_ACCESS_TOKEN = "kakao-access-token";
    private static final Long KAKAO_ID = 12345L;
    private static final long REFRESH_EXPIRATION_SECONDS = 60 * 60 * 24 * 7;

    @Mock
    private KakaoOAuthService kakaoOAuthService;

    @Mock
    private UserRepository userRepository;

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private JwtProvider jwtProvider;
    private AuthService authService;

    @BeforeEach
    void setUp() {
        jwtProvider = new JwtProvider(JWT_SECRET);
        authService = new AuthService(kakaoOAuthService, userRepository, jwtProvider, redisTemplate);
    }

    @Test
    void kakaoMobileLoginCreatesUserAndIssuesTokens() {
        KakaoUserInfo userInfo = new KakaoUserInfo(KAKAO_ID, "가은", "https://profile.image");
        User savedUser = user(10L, KAKAO_ID, "가은");

        when(kakaoOAuthService.getUserInfo(KAKAO_ACCESS_TOKEN)).thenReturn(userInfo);
        when(userRepository.findByKakaoId(KAKAO_ID)).thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenReturn(savedUser);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        TokenResponse response = authService.kakaoMobileLogin(KAKAO_ACCESS_TOKEN);

        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(userCaptor.capture());
        verify(valueOperations).set(
                eq(response.getRefreshToken()),
                eq("10"),
                eq(REFRESH_EXPIRATION_SECONDS),
                eq(TimeUnit.SECONDS)
        );

        assertThat(jwtProvider.getUserId(response.getAccessToken())).isEqualTo(10L);
        assertThat(response.getRefreshToken()).isNotBlank();
        assertThat(userCaptor.getValue().getKakaoId()).isEqualTo(KAKAO_ID);
        assertThat(userCaptor.getValue().getNickname()).isEqualTo("가은");
        assertThat(userCaptor.getValue().getProfileImage()).isEqualTo("https://profile.image");
    }

    @Test
    void kakaoMobileLoginIssuesTokensForExistingUser() {
        KakaoUserInfo userInfo = new KakaoUserInfo(KAKAO_ID, "가은", "https://profile.image");
        User existingUser = user(11L, KAKAO_ID, "기존 사용자");

        when(kakaoOAuthService.getUserInfo(KAKAO_ACCESS_TOKEN)).thenReturn(userInfo);
        when(userRepository.findByKakaoId(KAKAO_ID)).thenReturn(Optional.of(existingUser));
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);

        TokenResponse response = authService.kakaoMobileLogin(KAKAO_ACCESS_TOKEN);

        verify(userRepository, never()).save(any(User.class));
        verify(valueOperations).set(
                eq(response.getRefreshToken()),
                eq("11"),
                eq(REFRESH_EXPIRATION_SECONDS),
                eq(TimeUnit.SECONDS)
        );

        assertThat(jwtProvider.getUserId(response.getAccessToken())).isEqualTo(11L);
        assertThat(response.getRefreshToken()).isNotBlank();
    }

    @Test
    void kakaoMobileLoginFailsWhenKakaoUserInfoCannotBeRetrieved() {
        when(kakaoOAuthService.getUserInfo(KAKAO_ACCESS_TOKEN))
                .thenThrow(new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED));

        assertThatThrownBy(() -> authService.kakaoMobileLogin(KAKAO_ACCESS_TOKEN))
                .isInstanceOf(CustomException.class)
                .extracting("errorCode")
                .isEqualTo(ErrorCode.EXTERNAL_AUTH_FAILED);

        verify(userRepository, never()).findByKakaoId(any());
        verify(redisTemplate, never()).opsForValue();
    }

    private User user(Long id, Long kakaoId, String nickname) {
        return User.builder()
                .id(id)
                .kakaoId(kakaoId)
                .nickname(nickname)
                .profileImage("https://profile.image")
                .build();
    }
}
