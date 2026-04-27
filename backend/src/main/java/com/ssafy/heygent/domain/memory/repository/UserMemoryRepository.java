package com.ssafy.heygent.domain.memory.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
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

    @Query("""
        SELECT memory
        FROM UserMemory memory
        WHERE memory.userId = :userId
            AND memory.status = :status
            AND memory.confidence >= :confidence
            AND memory.importance >= :importance
            AND (memory.validFrom IS NULL OR memory.validFrom <= :now)
            AND (memory.validUntil IS NULL OR memory.validUntil > :now)
            AND (memory.expiresAt IS NULL OR memory.expiresAt > :now)
            AND (:storeType IS NULL OR memory.storeType = :storeType)
            AND (:memoryType IS NULL OR memory.memoryType = :memoryType)
            AND (:scopeType IS NULL OR memory.scopeType = :scopeType)
            AND (:scopeType IS NOT NULL OR memory.scopeType IS NULL OR memory.scopeType <> :excludedScopeType)
        ORDER BY memory.importance DESC, memory.confidence DESC, memory.updatedAt DESC
        """)
    List<UserMemory> findRecallCandidates(
        @Param("userId") Long userId,
        @Param("status") MemoryStatus status,
        @Param("confidence") Double confidence,
        @Param("importance") Double importance,
        @Param("now") java.time.LocalDateTime now,
        @Param("storeType") MemoryStoreType storeType,
        @Param("memoryType") MemoryType memoryType,
        @Param("scopeType") MemoryScopeType scopeType,
        @Param("excludedScopeType") MemoryScopeType excludedScopeType,
        Pageable pageable
    );

    @Query("""
        SELECT memory
        FROM UserMemory memory
        WHERE memory.userId = :userId
            AND (memory.storeType = :storeType OR memory.storeType IS NULL)
            AND memory.memoryType = :memoryType
            AND memory.scopeType = :scopeType
            AND memory.content = :content
            AND memory.status = :status
        ORDER BY memory.createdAt ASC
        """)
    Optional<UserMemory> findDuplicateActiveMemory(
        @Param("userId") Long userId,
        @Param("storeType") MemoryStoreType storeType,
        @Param("memoryType") MemoryType memoryType,
        @Param("scopeType") MemoryScopeType scopeType,
        @Param("content") String content,
        @Param("status") MemoryStatus status
    );
}
