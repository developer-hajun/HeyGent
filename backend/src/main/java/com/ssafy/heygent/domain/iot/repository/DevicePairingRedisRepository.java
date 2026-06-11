package com.ssafy.heygent.domain.iot.repository;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.iot.dto.DevicePairingSession;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

import java.time.Duration;
import java.util.List;
import java.util.Optional;

@Repository
@RequiredArgsConstructor
public class DevicePairingRedisRepository {

    private static final String CODE_KEY_PREFIX = "iot:pairing:code:";
    private static final String DEVICE_KEY_PREFIX = "iot:pairing:device:";

    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    public void savePendingSession(String pairCode, DevicePairingSession session, Duration ttl) {
        String value = serialize(session);
        redisTemplate.opsForValue().set(codeKey(pairCode), value, ttl);
        redisTemplate.opsForValue().set(deviceKey(session.deviceId()), value, ttl);
    }

    public Optional<DevicePairingSession> findByCode(String pairCode) {
        return findByKey(codeKey(pairCode));
    }

    public Optional<DevicePairingSession> findByDeviceId(String deviceId) {
        return findByKey(deviceKey(deviceId));
    }

    public boolean existsByCode(String pairCode) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(codeKey(pairCode)));
    }

    public void deleteByCodeAndDeviceId(String pairCode, String deviceId) {
        redisTemplate.delete(List.of(codeKey(pairCode), deviceKey(deviceId)));
    }

    private Optional<DevicePairingSession> findByKey(String key) {
        String value = redisTemplate.opsForValue().get(key);
        if (value == null) {
            return Optional.empty();
        }
        return Optional.of(deserialize(value));
    }

    private String serialize(DevicePairingSession session) {
        try {
            return objectMapper.writeValueAsString(session);
        } catch (JsonProcessingException exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

    private DevicePairingSession deserialize(String value) {
        try {
            return objectMapper.readValue(value, DevicePairingSession.class);
        } catch (JsonProcessingException exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

    private String codeKey(String pairCode) {
        return CODE_KEY_PREFIX + pairCode;
    }

    private String deviceKey(String deviceId) {
        return DEVICE_KEY_PREFIX + deviceId;
    }
}
