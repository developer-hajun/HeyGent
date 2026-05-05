package com.ssafy.heygent.domain.health.repository;

import com.ssafy.heygent.domain.health.entity.MeasurementLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MeasurementLogRepository extends JpaRepository<MeasurementLog, Long> {
    // 특정 사용자의 최신 로그 조회 등 추가 쿼리 정의 가능
    // List<MeasurementLog> findByUserOrderByMeasuredAtDesc(User user);
}
