package com.ssafy.heygent.domain.iot.service;

import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.repository.IotDeviceRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class DisplayEventPublishService {

    private static final String DEVICE_NOT_FOUND_REASON = "IoT device not found";
    private static final String DEVICE_INACTIVE_REASON = "IoT device inactive";

    private final IotDeviceRepository iotDeviceRepository;
    private final DisplayEventMapper displayEventMapper;
    private final MqttDisplayPublisher mqttDisplayPublisher;

    @Transactional(readOnly = true)
    public DisplayPublishResult publish(
        Long userId,
        DisplayEventType type,
        DisplayIcon icon,
        String sessionId,
        String stepRunId,
        String text
    ) {
        DisplayEventPayload payload = displayEventMapper.toPayload(type, icon, sessionId, stepRunId, text);
        return publish(userId, payload);
    }

    @Transactional(readOnly = true)
    public DisplayPublishResult publish(Long userId, DisplayEventPayload payload) {
        return iotDeviceRepository.findByUserId(userId)
            .map(device -> publishToDevice(userId, device, payload))
            .orElseGet(() -> skip(userId, DEVICE_NOT_FOUND_REASON, payload));
    }

    private DisplayPublishResult publishToDevice(Long userId, IotDevice device, DisplayEventPayload payload) {
        if (!device.isActive()) {
            return skip(userId, DEVICE_INACTIVE_REASON, payload);
        }
        return mqttDisplayPublisher.publish(device.getDeviceId(), payload);
    }

    private DisplayPublishResult skip(Long userId, String reason, DisplayEventPayload payload) {
        log.debug("Skip IoT display publish. userId={}, reason={}", userId, reason);
        return DisplayPublishResult.skipped(reason, payload);
    }
}
