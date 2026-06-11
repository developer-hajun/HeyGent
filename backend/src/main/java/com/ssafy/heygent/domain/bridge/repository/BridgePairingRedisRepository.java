package com.ssafy.heygent.domain.bridge.repository;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.bridge.dto.BridgePairingSession;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

import java.time.Duration;
import java.util.Optional;

@Repository
@RequiredArgsConstructor
public class BridgePairingRedisRepository {

    private static final String CODE_KEY_PREFIX = "bridge:pairing:code:";
    private static final String USER_KEY_PREFIX = "bridge:pairing:user:";

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    public void save(BridgePairingSession session, Duration ttl) {
        String value = serialize(session);
        redisTemplate.opsForValue().set(codeKey(session.code()), value, ttl);
        redisTemplate.opsForValue().set(userKey(session.userId()), session.code(), ttl);
    }

    public Optional<BridgePairingSession> findByCode(String code) {
        String value = redisTemplate.opsForValue().get(codeKey(code));
        if (value == null) {
            return Optional.empty();
        }
        return Optional.of(deserialize(value));
    }

    public Optional<BridgePairingSession> findByUserId(Long userId) {
        String code = redisTemplate.opsForValue().get(userKey(userId));
        if (code == null) {
            return Optional.empty();
        }
        return findByCode(code);
    }

    public boolean existsByCode(String code) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(codeKey(code)));
    }

    public void delete(String code, Long userId) {
        redisTemplate.delete(codeKey(code));
        redisTemplate.delete(userKey(userId));
    }

    private String serialize(BridgePairingSession session) {
        try {
            return objectMapper.writeValueAsString(session);
        } catch (JsonProcessingException exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

    private BridgePairingSession deserialize(String value) {
        try {
            return objectMapper.readValue(value, BridgePairingSession.class);
        } catch (JsonProcessingException exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

    private String codeKey(String code) {
        return CODE_KEY_PREFIX + code;
    }

    private String userKey(Long userId) {
        return USER_KEY_PREFIX + userId;
    }
}
