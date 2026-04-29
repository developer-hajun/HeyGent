package com.ssafy.heygent.domain.session.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.session.entity.ProductSession;

public interface ProductSessionRepository extends JpaRepository<ProductSession, Long> {

    Optional<ProductSession> findByIdAndUserId(Long id, Long userId);

    List<ProductSession> findByUserIdOrderByUpdatedAtDescCreatedAtDesc(Long userId);
}
