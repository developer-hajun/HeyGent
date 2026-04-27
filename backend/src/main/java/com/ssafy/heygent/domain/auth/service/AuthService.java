package com.ssafy.heygent.domain.auth.service;

import java.util.UUID;
import java.util.concurrent.TimeUnit;

import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.auth.dto.response.TokenResponse;
import com.ssafy.heygent.domain.auth.oauth.KakaoOAuthService;
import com.ssafy.heygent.domain.auth.oauth.KakaoUserInfo;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AuthService {

    private static final long DEV_USER_KAKAO_ID = -1L;
    private static final long DEV_USER_KAKAO_ID_OFFSET = 10_000L;
    private static final String DEV_USER_NICKNAME = "개발용 테스트 사용자";
    private static final String DEV_USER_PROFILE_IMAGE = "https://placehold.co/256x256?text=DEV";

    private final KakaoOAuthService kakaoOAuthService;
    private final UserRepository userRepository;
    private final JwtProvider jwtProvider;
    private final RedisTemplate<String, String> redisTemplate;

    private final long refreshExpirationSeconds = 60 * 60 * 24 * 7;

    @Transactional
    public TokenResponse kakaoLogin(String code) {

        String kakaoToken = kakaoOAuthService.getAccessToken(code);
        KakaoUserInfo userInfo = kakaoOAuthService.getUserInfo(kakaoToken);

        User user = userRepository.findByKakaoId(userInfo.getKakaoId())
                .orElseGet(()->userRepository.save(
                        User.builder()
                                .kakaoId(userInfo.getKakaoId())
                                .nickname(userInfo.getNickname())
                                .profileImage(userInfo.getProfileImage())
                                .build()
                ));

        return issueTokens(user);
    }

    @Transactional
    public TokenResponse devLogin() {

        return devLogin(null);
    }

    @Transactional
    public TokenResponse devLogin(String userKey) {

        Long devKakaoId = resolveDevKakaoId(userKey);
        String devNickname = resolveDevNickname(userKey);

        User devUser = userRepository.findByKakaoId(devKakaoId)
                .orElseGet(() -> userRepository.save(
                        User.builder()
                                .kakaoId(devKakaoId)
                                .nickname(devNickname)
                                .profileImage(DEV_USER_PROFILE_IMAGE)
                                .build()
                ));

        return issueTokens(devUser);
    }

    private Long resolveDevKakaoId(String userKey) {
        if (userKey == null || userKey.isBlank()) {
            return DEV_USER_KAKAO_ID;
        }
        return -1L * (Math.abs((long) userKey.trim().hashCode()) + DEV_USER_KAKAO_ID_OFFSET);
    }

    private String resolveDevNickname(String userKey) {
        if (userKey == null || userKey.isBlank()) {
            return DEV_USER_NICKNAME;
        }
        return DEV_USER_NICKNAME + " " + userKey.trim();
    }

    public void logout(String refreshToken) {

        Boolean exists = redisTemplate.hasKey(refreshToken);

        if (Boolean.FALSE.equals(exists)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        redisTemplate.delete(refreshToken);
    }


    public TokenResponse refresh(String refreshToken) {

        String userId = redisTemplate.opsForValue().get(refreshToken);

        if (userId == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        String newAccessToken = jwtProvider.createAccessToken(Long.valueOf(userId));

        return TokenResponse.builder()
                .accessToken(newAccessToken)
                .refreshToken(refreshToken)
                .build();
    }

    private TokenResponse issueTokens(User user) {

        String accessToken = jwtProvider.createAccessToken(user.getId());
        String refreshToken = UUID.randomUUID().toString();

        redisTemplate.opsForValue()
                .set(refreshToken, user.getId().toString(), refreshExpirationSeconds, TimeUnit.SECONDS);

        return TokenResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .build();
    }
}
