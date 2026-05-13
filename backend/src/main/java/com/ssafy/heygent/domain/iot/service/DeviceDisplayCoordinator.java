package com.ssafy.heygent.domain.iot.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.iot.dto.DeviceInteractionRequest;
import com.ssafy.heygent.domain.iot.dto.DeviceInteractionType;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayFocusState;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.InternalDisplayEventRequest;
import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.repository.DeviceDisplayStateRedisRepository;
import com.ssafy.heygent.domain.iot.repository.IotDeviceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.DigestUtils;
import org.springframework.util.StringUtils;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class DeviceDisplayCoordinator {

    private static final Duration START_SIGNAL_TTL = Duration.ofSeconds(2);
    private static final Duration DONE_SIGNAL_TTL = Duration.ofSeconds(3);
    private static final Duration WAITING_FOCUS_TTL = Duration.ofMinutes(30);
    private static final Duration MANUAL_FOCUS_TTL = Duration.ofSeconds(15);
    private static final DisplayEventPayload EMPTY_PAYLOAD = new DisplayEventPayload(
        DisplayEventType.INFO,
        "none",
        null,
        null,
        DisplayIcon.INFO,
        "none",
        null,
        0L,
        0,
        "IDLE",
        null,
        false,
        0L
    );

    private final DisplayEventMapper displayEventMapper;
    private final DisplayEventPublishService displayEventPublishService;
    private final DeviceDisplayStateRedisRepository displayStateRepository;
    private final IotDeviceRepository iotDeviceRepository;
    private final ObjectMapper objectMapper;

    public DisplayPublishResult publishInternal(InternalDisplayEventRequest request) {
        DisplayEventPayload payload = displayEventMapper.toPayload(
            request.type(),
            request.icon(),
            request.sessionId(),
            request.taskRunId(),
            request.stepRunId(),
            request.text(),
            request.textKey(),
            request.ttlMs(),
            request.priority() == null ? 0 : request.priority(),
            request.renderMode(),
            request.statusKind(),
            Boolean.TRUE.equals(request.focus())
        );

        displayStateRepository.saveTaskPayload(request.userId(), payload);
        DisplayEventPayload focusedPayload = selectFocusedPayload(request.userId(), payload);
        return publishIfChanged(request.userId(), focusedPayload);
    }

    public DisplayPublishResult handleInteraction(Long userId, String deviceId, DeviceInteractionRequest request) {
        if (request.interactionType() != DeviceInteractionType.SHORT_PRESS) {
            return DisplayPublishResult.skipped("Unsupported interaction", EMPTY_PAYLOAD);
        }
        if (!ownsDevice(userId, deviceId)) {
            return DisplayPublishResult.skipped("IoT device not found", EMPTY_PAYLOAD);
        }

        List<DisplayEventPayload> activePayloads = displayStateRepository.listActivePayloads(userId);
        if (activePayloads.isEmpty()) {
            return DisplayPublishResult.skipped("No active task", EMPTY_PAYLOAD);
        }

        String currentTaskRunId = displayStateRepository.findFocus(userId)
            .map(DisplayFocusState::taskRunId)
            .filter(StringUtils::hasText)
            .orElse(request.currentTaskRunId());
        DisplayEventPayload nextPayload = nextPayload(activePayloads, currentTaskRunId);
        displayStateRepository.saveFocus(
            userId,
            new DisplayFocusState(nextPayload.taskRunId(), "MANUAL_TOUCH", expiresAt(MANUAL_FOCUS_TTL)),
            MANUAL_FOCUS_TTL
        );
        return publishIfChanged(userId, nextPayload);
    }

    private DisplayEventPayload selectFocusedPayload(Long userId, DisplayEventPayload incoming) {
        if (isWaiting(incoming)) {
            saveFocus(userId, incoming, "WAITING_OVERRIDE", WAITING_FOCUS_TTL);
            return incoming;
        }
        if (incoming.type() != null && incoming.type().name().equals("STARTED")) {
            saveFocus(userId, incoming, "START_SIGNAL", START_SIGNAL_TTL);
            return incoming;
        }
        if (isTerminal(incoming)) {
            saveFocus(userId, incoming, "DONE_SIGNAL", DONE_SIGNAL_TTL);
            return incoming;
        }

        Optional<DisplayEventPayload> manualPayload = activeManualFocusPayload(userId);
        if (manualPayload.isPresent()) {
            return manualPayload.get();
        }

        return displayStateRepository.listActivePayloads(userId).stream()
            .findFirst()
            .orElse(incoming);
    }

    private void saveFocus(Long userId, DisplayEventPayload payload, String reason, Duration ttl) {
        if (!StringUtils.hasText(payload.taskRunId())) {
            return;
        }
        displayStateRepository.saveFocus(
            userId,
            new DisplayFocusState(payload.taskRunId(), reason, expiresAt(ttl)),
            ttl
        );
    }

    private Optional<DisplayEventPayload> activeManualFocusPayload(Long userId) {
        long now = Instant.now().toEpochMilli();
        return displayStateRepository.findFocus(userId)
            .filter(focus -> "MANUAL_TOUCH".equals(focus.reason()))
            .filter(focus -> focus.expiresAtEpochMs() > now)
            .map(DisplayFocusState::taskRunId)
            .flatMap(displayStateRepository::findTaskPayload);
    }

    private DisplayEventPayload nextPayload(List<DisplayEventPayload> payloads, String currentTaskRunId) {
        if (!StringUtils.hasText(currentTaskRunId)) {
            return payloads.get(0);
        }
        for (int index = 0; index < payloads.size(); index++) {
            if (currentTaskRunId.equals(payloads.get(index).taskRunId())) {
                return payloads.get((index + 1) % payloads.size());
            }
        }
        return payloads.get(0);
    }

    private DisplayPublishResult publishIfChanged(Long userId, DisplayEventPayload payload) {
        String hash = payloadHash(payload);
        Optional<String> previousHash = displayStateRepository.findLastSentHash(userId);
        if (previousHash.filter(hash::equals).isPresent()) {
            return DisplayPublishResult.skipped("Duplicate display payload", payload);
        }
        DisplayPublishResult result = displayEventPublishService.publish(userId, payload);
        if (result.published()) {
            displayStateRepository.saveLastSentHash(userId, hash);
        }
        return result;
    }

    private boolean ownsDevice(Long userId, String deviceId) {
        return iotDeviceRepository.findByDeviceIdAndUserId(deviceId, userId)
            .map(IotDevice::isActive)
            .orElse(false);
    }

    private boolean isWaiting(DisplayEventPayload payload) {
        return payload.type() != null && payload.type().name().equals("WAITING");
    }

    private boolean isTerminal(DisplayEventPayload payload) {
        if (payload.type() == null) {
            return false;
        }
        return switch (payload.type()) {
            case DONE, FAILED, CANCELED -> true;
            case STARTED, STEP, WAITING, INFO -> false;
        };
    }

    private long expiresAt(Duration ttl) {
        return Instant.now().plus(ttl).toEpochMilli();
    }

    private String payloadHash(DisplayEventPayload payload) {
        try {
            String value = objectMapper.writeValueAsString(payload);
            return DigestUtils.md5DigestAsHex(value.getBytes(StandardCharsets.UTF_8));
        } catch (JsonProcessingException exception) {
            return DigestUtils.md5DigestAsHex(String.valueOf(payload).getBytes(StandardCharsets.UTF_8));
        }
    }
}
