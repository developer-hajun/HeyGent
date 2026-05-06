package com.ssafy.heygent.domain.iot.service;

import com.ssafy.heygent.domain.iot.dto.DevicePairRequest;
import com.ssafy.heygent.domain.iot.dto.DevicePairingSession;
import com.ssafy.heygent.domain.iot.dto.DevicePairingStatus;
import com.ssafy.heygent.domain.iot.dto.DeviceResponse;
import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;
import com.ssafy.heygent.domain.iot.dto.DisplayPairingStartRequest;
import com.ssafy.heygent.domain.iot.dto.DisplayPairingStartResponse;
import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.entity.IotDeviceStatus;
import com.ssafy.heygent.domain.iot.repository.DevicePairingRedisRepository;
import com.ssafy.heygent.domain.iot.repository.IotDeviceRepository;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class DevicePairingService {

    private static final int PAIR_CODE_BOUND = 1_000_000;
    private static final int PAIR_CODE_LENGTH = 6;
    private static final int PAIR_CODE_MAX_ATTEMPTS = 10;
    private static final Duration PAIRING_TTL = Duration.ofMinutes(5);
    private static final String PAIRING_SESSION_ID = "pairing";
    private static final String CONNECTED_TEXT = "connected";

    private final DevicePairingRedisRepository pairingRedisRepository;
    private final IotDeviceRepository iotDeviceRepository;
    private final UserRepository userRepository;
    private final DisplayEventMapper displayEventMapper;
    private final MqttDisplayPublisher mqttDisplayPublisher;
    private final SecureRandom secureRandom = new SecureRandom();

    public DisplayPairingStartResponse start(DisplayPairingStartRequest request) {
        String deviceId = normalizeDeviceId(request.deviceId());
        if (iotDeviceRepository.existsByDeviceId(deviceId)) {
            throw new CustomException(ErrorCode.DEVICE_ALREADY_PAIRED);
        }

        pairingRedisRepository.findByDeviceId(deviceId)
            .ifPresent(session -> pairingRedisRepository.deleteByCodeAndDeviceId(session.pairCode(), deviceId));

        String pairCode = generatePairCode();
        LocalDateTime createdAt = LocalDateTime.now();
        DevicePairingSession session = DevicePairingSession.pending(
            pairCode,
            deviceId,
            trimToNull(request.nonce()),
            trimToNull(request.firmwareVersion()),
            createdAt,
            createdAt.plus(PAIRING_TTL)
        );

        pairingRedisRepository.savePendingSession(pairCode, session, PAIRING_TTL);
        return new DisplayPairingStartResponse(pairCode, PAIRING_TTL.toSeconds());
    }

    @Transactional
    public DeviceResponse pair(Long userId, DevicePairRequest request) {
        DevicePairingSession session = pairingRedisRepository.findByCode(request.pairCode())
            .orElseThrow(() -> new CustomException(ErrorCode.PAIR_CODE_NOT_FOUND));

        validatePendingSession(session);

        String deviceId = session.deviceId();
        if (iotDeviceRepository.existsByDeviceId(deviceId)) {
            throw new CustomException(ErrorCode.DEVICE_ALREADY_PAIRED);
        }
        if (iotDeviceRepository.existsByUserId(userId)) {
            throw new CustomException(ErrorCode.USER_DEVICE_LIMIT_EXCEEDED);
        }

        User user = userRepository.findById(userId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        IotDevice device = IotDevice.builder()
            .user(user)
            .deviceId(deviceId)
            .displayName(resolveDisplayName(request, deviceId))
            .status(IotDeviceStatus.ACTIVE)
            .build();

        IotDevice savedDevice = iotDeviceRepository.save(device);
        pairingRedisRepository.deleteByCodeAndDeviceId(session.pairCode(), deviceId);
        publishConnected(deviceId);
        return DeviceResponse.from(savedDevice);
    }

    private void validatePendingSession(DevicePairingSession session) {
        if (session.status() != DevicePairingStatus.PENDING) {
            throw new CustomException(ErrorCode.PAIR_CODE_NOT_FOUND);
        }
        if (session.expiresAt() != null && session.expiresAt().isBefore(LocalDateTime.now())) {
            pairingRedisRepository.deleteByCodeAndDeviceId(session.pairCode(), session.deviceId());
            throw new CustomException(ErrorCode.PAIR_CODE_EXPIRED);
        }
    }

    private void publishConnected(String deviceId) {
        DisplayEventPayload payload = displayEventMapper.toPayload(
            DisplayEventType.INFO,
            DisplayIcon.SUCCESS,
            PAIRING_SESSION_ID,
            PAIRING_SESSION_ID,
            CONNECTED_TEXT
        );
        mqttDisplayPublisher.publish(deviceId, payload);
    }

    private String generatePairCode() {
        for (int i = 0; i < PAIR_CODE_MAX_ATTEMPTS; i++) {
            String pairCode = String.format("%0" + PAIR_CODE_LENGTH + "d", secureRandom.nextInt(PAIR_CODE_BOUND));
            if (!pairingRedisRepository.existsByCode(pairCode)) {
                return pairCode;
            }
        }
        throw new CustomException(ErrorCode.CONFLICT);
    }

    private String normalizeDeviceId(String deviceId) {
        return deviceId.trim();
    }

    private String resolveDisplayName(DevicePairRequest request, String deviceId) {
        if (StringUtils.hasText(request.displayName())) {
            return request.displayName().trim();
        }
        return deviceId;
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}
