package com.ssafy.heygent.domain.health.repository;

import com.ssafy.heygent.domain.health.entity.MeasurementLog;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface MeasurementLogRepository extends JpaRepository<MeasurementLog, Long> {

    @EntityGraph(attributePaths = {"dailyActivity", "physicalProfile", "vitalLog", "sleepRecord"})
    Optional<MeasurementLog> findTopByUser_IdOrderByMeasuredAtDesc(Long userId);
}
