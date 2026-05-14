package com.ssafy.heygent.domain.bridge.service;

import com.ssafy.heygent.domain.bridge.client.AiBridgeStatusClient;
import com.ssafy.heygent.domain.bridge.dto.BridgeDeviceResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgeInternalAuthValidateResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgePairRequest;
import com.ssafy.heygent.domain.bridge.dto.BridgePairResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgePairingCodeResponse;
import com.ssafy.heygent.domain.bridge.dto.BridgePairingSession;
import com.ssafy.heygent.domain.bridge.entity.BridgeDevice;
import com.ssafy.heygent.domain.bridge.repository.BridgeDeviceRepository;
import com.ssafy.heygent.domain.bridge.repository.BridgePairingRedisRepository;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import java.util.Set;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.List;

@Service
@RequiredArgsConstructor
public class BridgeService {

    private static final Duration PAIRING_TTL = Duration.ofMinutes(5);
    private static final int CODE_RANDOM_TRY_LIMIT = 10;
    private static final SecureRandom RANDOM = new SecureRandom();

    private final BridgeDeviceRepository bridgeDeviceRepository;
    private final BridgePairingRedisRepository bridgePairingRedisRepository;
    private final UserRepository userRepository;
    private final AiBridgeStatusClient aiBridgeStatusClient;

    @Transactional
    public BridgePairingCodeResponse issuePairingCode(Long userId) {
        // 동일 user 가 진행 중인 코드가 있으면 그대로 반환해서 중복 발급을 막는다.
        return bridgePairingRedisRepository.findByUserId(userId)
            .map(existing -> new BridgePairingCodeResponse(existing.code(), existing.expiresAt()))
            .orElseGet(() -> generateAndSave(userId));
    }

    @Transactional
    public BridgePairResponse pair(BridgePairRequest request) {
        BridgePairingSession pairing = bridgePairingRedisRepository.findByCode(request.code())
            .orElseThrow(() -> new CustomException(ErrorCode.BRIDGE_PAIRING_NOT_FOUND));

        // Redis TTL 이 살아있어도 expiresAt 보다 늦게 도착하면 보수적으로 만료 처리한다.
        if (pairing.expiresAt() != null && pairing.expiresAt().isBefore(Instant.now())) {
            bridgePairingRedisRepository.delete(pairing.code(), pairing.userId());
            throw new CustomException(ErrorCode.BRIDGE_PAIRING_EXPIRED);
        }

        User user = userRepository.findById(pairing.userId())
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        // 같은 user 의 활성(미폐기) 디바이스 중 이름이 같은 것이 있으면 거절한다.
        // 사용자가 옛 PC 의 브릿지를 끄지 않고 새 PC 에 같은 이름으로 페어링하려는 케이스 방지.
        String trimmedName = request.deviceName().trim();
        boolean nameInUse = bridgeDeviceRepository
            .findAllByUserIdAndRevokedAtIsNullOrderByCreatedAtDesc(user.getId())
            .stream()
            .anyMatch(device -> device.getDeviceName().equalsIgnoreCase(trimmedName));
        if (nameInUse) {
            throw new CustomException(ErrorCode.BRIDGE_DEVICE_NAME_DUPLICATE);
        }

        // 1슬롯 정책: 이 user 의 기존 활성 디바이스를 모두 폐기한다.
        // 컨테이너 TZ 와 무관하게 UTC 기준으로 시각을 기록해 두면 응답 매핑에서 'Z' 마커가 안정적으로 붙는다.
        LocalDateTime nowUtc = LocalDateTime.now(ZoneOffset.UTC);
        List<BridgeDevice> previous =
            bridgeDeviceRepository.findAllByUserIdAndRevokedAtIsNullOrderByCreatedAtDesc(user.getId());
        for (BridgeDevice device : previous) {
            device.revoke(nowUtc);
        }

        String rawToken = generateBridgeToken();
        BridgeDevice device = bridgeDeviceRepository.save(
            BridgeDevice.builder()
                .user(user)
                .deviceName(request.deviceName().trim())
                .tokenHash(sha256Hex(rawToken))
                .build()
        );

        bridgePairingRedisRepository.delete(pairing.code(), pairing.userId());

        return new BridgePairResponse(rawToken, device.getId(), user.getId(), device.getDeviceName());
    }

    @Transactional(readOnly = true)
    public List<BridgeDeviceResponse> listDevices(Long userId) {
        Set<Long> onlineUserIds = aiBridgeStatusClient.fetchOnlineUserIds();
        boolean userOnline = onlineUserIds.contains(userId);
        // user 가 AI 서버에 현재 붙어있다면 그 user 의 디바이스 중 활성(미폐기) 인 것이 online.
        // 폐기된 디바이스는 무조건 offline.
        return bridgeDeviceRepository.findAllByUserIdOrderByCreatedAtDesc(userId).stream()
            .map(device -> BridgeDeviceResponse.from(device, userOnline && device.isActive()))
            .toList();
    }

    @Transactional
    public void revokeDevice(Long userId, Long deviceId) {
        // 동일 엔드포인트가 두 가지 동작을 자동 분기한다:
        //  - 활성 디바이스: revoke (토큰 무효화 + 히스토리 행은 보존)
        //  - 이미 revoke 된 디바이스: 완전 삭제 (사용자가 "X" 로 히스토리 정리)
        BridgeDevice device = bridgeDeviceRepository.findByIdAndUserId(deviceId, userId)
            .orElseThrow(() -> new CustomException(ErrorCode.BRIDGE_DEVICE_NOT_FOUND));
        if (device.isActive()) {
            device.revoke(LocalDateTime.now(ZoneOffset.UTC));
        } else {
            bridgeDeviceRepository.delete(device);
        }
    }

    @Transactional
    public void unpairByToken(String bridgeToken) {
        // 브릿지 PC 가 자기 토큰으로 자기 디바이스만 폐기할 수 있게 한다.
        // 토큰을 모르는 다른 PC 는 이 엔드포인트로 다른 사람 디바이스를 건드릴 수 없다.
        BridgeDevice device = bridgeDeviceRepository.findByTokenHash(sha256Hex(bridgeToken))
            .orElseThrow(() -> new CustomException(ErrorCode.BRIDGE_TOKEN_INVALID));
        if (device.isActive()) {
            device.revoke(LocalDateTime.now(ZoneOffset.UTC));
        }
    }

    @Transactional
    public BridgeInternalAuthValidateResponse validateBridgeToken(String bridgeToken) {
        BridgeDevice device = bridgeDeviceRepository.findByTokenHash(sha256Hex(bridgeToken))
            .orElseThrow(() -> new CustomException(ErrorCode.BRIDGE_TOKEN_INVALID));
        if (!device.isActive()) {
            throw new CustomException(ErrorCode.BRIDGE_TOKEN_REVOKED);
        }
        device.markSeen(LocalDateTime.now(ZoneOffset.UTC));
        return new BridgeInternalAuthValidateResponse(
            device.getUser().getId(),
            device.getId(),
            device.getDeviceName()
        );
    }

    private BridgePairingCodeResponse generateAndSave(Long userId) {
        String code = newUniqueCode();
        Instant now = Instant.now();
        Instant expiresAt = now.plus(PAIRING_TTL);
        BridgePairingSession session = new BridgePairingSession(code, userId, now, expiresAt);
        bridgePairingRedisRepository.save(session, PAIRING_TTL);
        return new BridgePairingCodeResponse(code, expiresAt);
    }

    private String newUniqueCode() {
        for (int attempt = 0; attempt < CODE_RANDOM_TRY_LIMIT; attempt++) {
            String candidate = String.format("%06d", RANDOM.nextInt(1_000_000));
            if (!bridgePairingRedisRepository.existsByCode(candidate)) {
                return candidate;
            }
        }
        throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
    }

    private String generateBridgeToken() {
        byte[] buffer = new byte[32];
        RANDOM.nextBytes(buffer);
        // URL-safe base64 대신 16진수로 두면 환경변수/.env 에 그대로 박기 쉽다.
        return HexFormat.of().formatHex(buffer);
    }

    private String sha256Hex(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException exception) {
            throw new CustomException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }
}
