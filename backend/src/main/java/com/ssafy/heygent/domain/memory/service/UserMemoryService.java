package com.ssafy.heygent.domain.memory.service;

import java.time.LocalDateTime;
import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.UserMemory;
import com.ssafy.heygent.domain.memory.repository.UserMemoryRepository;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserMemoryService {

    private static final double MIN_IMPORTANCE_TO_STORE = 0.5;
    private static final double MIN_CONFIDENCE_TO_STORE = 0.7;
    private static final int DEFAULT_RECALL_LIMIT = 5;
    private static final int MAX_RECALL_LIMIT = 20;

    private final UserMemoryRepository userMemoryRepository;

    @Transactional
    public UserMemoryResponse create(Long userId, CreateMemoryRequest request) {
        validateMemoryScore(request.getImportance(), request.getConfidence());

        UserMemory memory = UserMemory.builder()
            .userId(userId)
            .memoryType(request.getMemoryType())
            .content(request.getContent().trim())
            .summary(trimToNull(request.getSummary()))
            .importance(request.getImportance())
            .confidence(request.getConfidence())
            .status(MemoryStatus.ACTIVE)
            .sourceSessionKey(trimToNull(request.getSourceSessionKey()))
            .sourceTaskRunId(trimToNull(request.getSourceTaskRunId()))
            .build();

        return UserMemoryResponse.from(userMemoryRepository.save(memory));
    }

    public List<UserMemoryResponse> getMyMemories(Long userId) {
        return userMemoryRepository.findByUserIdAndStatusOrderByImportanceDescCreatedAtDesc(
                userId,
                MemoryStatus.ACTIVE
            )
            .stream()
            .map(UserMemoryResponse::from)
            .toList();
    }

    @Transactional
    public List<UserMemoryResponse> recall(Long userId, Integer limit) {
        int normalizedLimit = normalizeRecallLimit(limit);
        List<UserMemory> memories = userMemoryRepository
            .findByUserIdAndStatusAndConfidenceGreaterThanEqualAndImportanceGreaterThanEqualOrderByImportanceDescUpdatedAtDesc(
                userId,
                MemoryStatus.ACTIVE,
                MIN_CONFIDENCE_TO_STORE,
                MIN_IMPORTANCE_TO_STORE,
                PageRequest.of(0, normalizedLimit)
            );

        LocalDateTime accessedAt = LocalDateTime.now();
        memories.forEach(memory -> memory.markAccessed(accessedAt));

        return memories.stream()
            .map(UserMemoryResponse::from)
            .toList();
    }

    @Transactional
    public void delete(Long userId, Long memoryId) {
        UserMemory memory = userMemoryRepository.findById(memoryId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        if (memory.getStatus() == MemoryStatus.DELETED) {
            throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
        }
        if (!memory.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }

        memory.delete();
    }

    private void validateMemoryScore(Double importance, Double confidence) {
        if (importance < MIN_IMPORTANCE_TO_STORE || confidence < MIN_CONFIDENCE_TO_STORE) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private int normalizeRecallLimit(Integer limit) {
        if (limit == null) {
            return DEFAULT_RECALL_LIMIT;
        }
        if (limit < 1) {
            return DEFAULT_RECALL_LIMIT;
        }
        return Math.min(limit, MAX_RECALL_LIMIT);
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}
