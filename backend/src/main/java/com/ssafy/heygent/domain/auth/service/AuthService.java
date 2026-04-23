package com.ssafy.heygent.domain.auth.service;

import com.ssafy.heygent.domain.auth.dto.response.TokenResponse;
import com.ssafy.heygent.domain.auth.oauth.KakaoOAuthService;
import com.ssafy.heygent.domain.auth.oauth.KakaoUserInfo;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final KakaoOAuthService kakaoOAuthService;
    private final UserRepository userRepository;
    private final JwtProvider jwtProvider;
    private final RedisTemplate<String, String> redisTemplate;

    private final long REFRESH_EXP = 60 * 60 * 24 * 7;

    @Transactional
    public TokenResponse kakaoLogin(String code){

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

        String accessToken = jwtProvider.createAccessToken(user.getId());
        String refreshToken = UUID.randomUUID().toString();

        redisTemplate.opsForValue()
                .set(refreshToken, user.getId().toString(), REFRESH_EXP, TimeUnit.SECONDS);

        return TokenResponse.builder()
                .accessToken(accessToken)
                .build();
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
}
