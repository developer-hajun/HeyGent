package com.ssafy.heygent.domain.iot.repository;

import com.ssafy.heygent.domain.iot.entity.IotDevice;
import com.ssafy.heygent.domain.iot.entity.IotDeviceStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface IotDeviceRepository extends JpaRepository<IotDevice, Long> {

    boolean existsByDeviceId(String deviceId);

    boolean existsByUserId(Long userId);

    Optional<IotDevice> findByDeviceId(String deviceId);

    Optional<IotDevice> findByUserId(Long userId);

    Optional<IotDevice> findByDeviceIdAndUserId(String deviceId, Long userId);

    List<IotDevice> findAllByUserIdOrderByCreatedAtDesc(Long userId);

    List<IotDevice> findAllByUserIdAndStatus(Long userId, IotDeviceStatus status);
}
