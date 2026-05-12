package com.ssafy.heygent.domain.bridge.repository;

import com.ssafy.heygent.domain.bridge.entity.BridgeDevice;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface BridgeDeviceRepository extends JpaRepository<BridgeDevice, Long> {

    Optional<BridgeDevice> findByTokenHash(String tokenHash);

    Optional<BridgeDevice> findByIdAndUserId(Long id, Long userId);

    List<BridgeDevice> findAllByUserIdAndRevokedAtIsNullOrderByCreatedAtDesc(Long userId);

    List<BridgeDevice> findAllByUserIdOrderByCreatedAtDesc(Long userId);
}
