package com.ssafy.heygent.domain.auth.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.auth.dto.response.AuthVerificationResponse;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;

@Service
public class AuthVerificationService {

    private static final List<String> DEFAULT_SCOPES = List.of("USER");

    private final UserRepository userRepository;
    private final JwtProvider jwtProvider;
    private final String configuredInternalServiceToken;

    public AuthVerificationService(
        UserRepository userRepository,
        JwtProvider jwtProvider,
        @Value("${internal.ai.service-token:}") String configuredInternalServiceToken
    ) {
        this.userRepository = userRepository;
        this.jwtProvider = jwtProvider;
        this.configuredInternalServiceToken = configuredInternalServiceToken;
    }

    public AuthVerificationResponse verify(String internalServiceToken, String accessToken) {
        verifyInternalCaller(internalServiceToken);

        Claims claims = parseAccessToken(accessToken);
        Long userId = extractUserId(claims);

        userRepository.findById(userId)
            .orElseThrow(() -> new CustomException(ErrorCode.INVALID_TOKEN));

        return AuthVerificationResponse.builder()
            .userId(userId)
            .workspaceKey(null)
            .scopes(DEFAULT_SCOPES)
            .tokenExpiresAt(toInstant(claims))
            .build();
    }

    private void verifyInternalCaller(String internalServiceToken) {
        /*
         * 사용자 JWT 검증은 최종 사용자의 신원을 확인하기 위한 절차이고,
         * 내부 호출자 검증은 이 API를 호출할 수 있는 서버를 제한하기 위한 절차다.
         * 두 토큰의 책임이 다르므로 사용자 Authorization 인증 필터와 분리해 전용 헤더를 검증한다.
         */
        if (!matchesInternalServiceToken(internalServiceToken)) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }
    }

    private boolean matchesInternalServiceToken(String internalServiceToken) {
        if (!StringUtils.hasText(internalServiceToken)
            || !StringUtils.hasText(configuredInternalServiceToken)) {
            return false;
        }

        byte[] provided = internalServiceToken.getBytes(StandardCharsets.UTF_8);
        byte[] configured = configuredInternalServiceToken.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(provided, configured);
    }

    private Claims parseAccessToken(String accessToken) {
        if (!StringUtils.hasText(accessToken)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        try {
            return jwtProvider.parseClaims(accessToken);
        } catch (JwtException | IllegalArgumentException exception) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
    }

    private Long extractUserId(Claims claims) {
        try {
            return Long.valueOf(claims.getSubject());
        } catch (RuntimeException exception) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
    }

    private Instant toInstant(Claims claims) {
        if (claims.getExpiration() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        return claims.getExpiration().toInstant();
    }
}
