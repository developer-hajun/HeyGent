package com.ssafy.heygent.domain.memory.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;

public interface UserMemoryRepository extends JpaRepository<UserMemory, Long> {

    List<UserMemory> findByUserIdAndStatusOrderByImportanceDescCreatedAtDesc(
        Long userId,
        MemoryStatus status
    );

    List<UserMemory> findByUserIdAndStatusAndConfidenceGreaterThanEqualAndImportanceGreaterThanEqualOrderByImportanceDescUpdatedAtDesc(
        Long userId,
        MemoryStatus status,
        Double confidence,
        Double importance,
        Pageable pageable
    );

    Optional<UserMemory> findFirstByUserIdAndMemoryTypeAndContentAndStatus(
        Long userId,
        MemoryType memoryType,
        String content,
        MemoryStatus status
    );
}
