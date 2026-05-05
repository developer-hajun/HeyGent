package com.ssafy.heygent.domain.iot.service;

import com.ssafy.heygent.domain.iot.dto.DeviceRegisterRequest;
import com.ssafy.heygent.domain.iot.dto.DeviceResponse;
import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishTestRequest;
import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.entity.IotDeviceStatus;
import com.ssafy.heygent.domain.iot.repository.IotDeviceRepository;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.List;

@Service
@RequiredArgsConstructor
public class DeviceService {

    private final IotDeviceRepository iotDeviceRepository;
    private final UserRepository userRepository;
    private final DisplayEventMapper displayEventMapper;
    private final MqttDisplayPublisher mqttDisplayPublisher;

    @Transactional
    public DeviceResponse register(Long userId, DeviceRegisterRequest request) {
        if (iotDeviceRepository.existsByDeviceId(request.deviceId())) {
            throw new CustomException(ErrorCode.DEVICE_ALREADY_PAIRED);
        }
        if (iotDeviceRepository.existsByUserId(userId)) {
            throw new CustomException(ErrorCode.USER_DEVICE_LIMIT_EXCEEDED);
        }

        User user = userRepository.findById(userId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        IotDevice device = IotDevice.builder()
            .user(user)
            .deviceId(request.deviceId())
            .displayName(resolveDisplayName(request))
            .status(IotDeviceStatus.ACTIVE)
            .build();

        return DeviceResponse.from(iotDeviceRepository.save(device));
    }

    @Transactional(readOnly = true)
    public List<DeviceResponse> list(Long userId) {
        return iotDeviceRepository.findAllByUserIdOrderByCreatedAtDesc(userId)
            .stream()
            .map(DeviceResponse::from)
            .toList();
    }

    @Transactional
    public DeviceResponse updateStatus(Long userId, String deviceId, IotDeviceStatus status) {
        IotDevice device = findOwnedDevice(userId, deviceId);
        device.updateStatus(status);
        return DeviceResponse.from(device);
    }

    @Transactional(readOnly = true)
    public DisplayPublishResult publishTest(Long userId, String deviceId, DisplayPublishTestRequest request) {
        IotDevice device = findOwnedDevice(userId, deviceId);
        if (!device.isActive()) {
            throw new CustomException(ErrorCode.DEVICE_INACTIVE);
        }

        DisplayEventPayload payload = displayEventMapper.toPayload(
            request.type(),
            request.icon(),
            request.sessionId(),
            request.stepRunId(),
            request.text()
        );

        return mqttDisplayPublisher.publish(device.getDeviceId(), payload);
    }

    private IotDevice findOwnedDevice(Long userId, String deviceId) {
        return iotDeviceRepository.findByDeviceIdAndUserId(deviceId, userId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }

    private String resolveDisplayName(DeviceRegisterRequest request) {
        if (StringUtils.hasText(request.displayName())) {
            return request.displayName().trim();
        }
        return request.deviceId();
    }
}
