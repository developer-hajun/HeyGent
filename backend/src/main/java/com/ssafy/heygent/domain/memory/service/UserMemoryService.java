package com.ssafy.heygent.domain.memory.service;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryCandidatesRequest;
import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.embedding.MemoryEmbeddingService;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;
import com.ssafy.heygent.domain.memory.repository.UserMemoryRepository;
import com.ssafy.heygent.domain.memory.repository.UserMemoryVectorRepository;
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
    private static final int RECALL_FALLBACK_CANDIDATE_SIZE = 100;

    private final UserMemoryRepository userMemoryRepository;
    private final UserMemoryVectorRepository userMemoryVectorRepository;
    private final MemoryEmbeddingService memoryEmbeddingService;

    @Transactional
    public UserMemoryResponse create(Long userId, CreateMemoryRequest request) {
        validateMemoryScore(request.getImportance(), request.getConfidence());
        String normalizedContent = request.getContent().trim();
        MemoryScopeType scopeType = resolveScopeType(request.getScopeType());

        return userMemoryRepository.findFirstByUserIdAndMemoryTypeAndScopeTypeAndContentAndStatus(
                userId,
                request.getMemoryType(),
                scopeType,
                normalizedContent,
                MemoryStatus.ACTIVE
            )
            .map(UserMemoryResponse::from)
            .orElseGet(() -> saveMemory(userId, request, scopeType, normalizedContent));
    }

    @Transactional
    public List<UserMemoryResponse> createCandidates(Long userId, CreateMemoryCandidatesRequest request) {
        return request.getCandidates().stream()
            .filter(candidate -> isStorableScore(candidate.getImportance(), candidate.getConfidence()))
            .map(candidate -> create(userId, candidate))
            .toList();
    }

    private UserMemoryResponse saveMemory(
        Long userId,
        CreateMemoryRequest request,
        MemoryScopeType scopeType,
        String normalizedContent
    ) {

        UserMemory memory = UserMemory.builder()
            .userId(userId)
            .memoryType(request.getMemoryType())
            .scopeType(scopeType)
            .content(normalizedContent)
            .summary(trimToNull(request.getSummary()))
            .metadata(normalizeMetadata(request.getMetadata()))
            .importance(request.getImportance())
            .confidence(request.getConfidence())
            .status(MemoryStatus.ACTIVE)
            .sourceSessionKey(trimToNull(request.getSourceSessionKey()))
            .sourceTaskRunId(trimToNull(request.getSourceTaskRunId()))
            .build();

        UserMemory savedMemory = userMemoryRepository.save(memory);
        userMemoryVectorRepository.updateEmbedding(
            savedMemory.getId(),
            memoryEmbeddingService.embed(buildEmbeddingText(savedMemory))
        );
        return UserMemoryResponse.from(savedMemory);
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
    public List<UserMemoryResponse> recall(
        Long userId,
        Integer limit,
        String query,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        int normalizedLimit = normalizeRecallLimit(limit);
        List<UserMemory> memories;

        if (StringUtils.hasText(query)) {
            memories = recallByEmbedding(
                userId,
                normalizedLimit,
                query,
                memoryType,
                scopeType,
                workspaceKey,
                sessionKey,
                resourceId,
                tags
            );
        } else {
            memories = recallByFilters(
                userId,
                normalizedLimit,
                memoryType,
                scopeType,
                workspaceKey,
                sessionKey,
                resourceId,
                tags
            );
        }

        LocalDateTime accessedAt = LocalDateTime.now();
        memories.forEach(memory -> memory.markAccessed(accessedAt));

        return memories.stream()
            .map(UserMemoryResponse::from)
            .toList();
    }

    private List<UserMemory> recallByEmbedding(
        Long userId,
        int limit,
        String query,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        List<Double> queryEmbedding = memoryEmbeddingService.embed(query.trim());
        List<Long> memoryIds = userMemoryVectorRepository.searchIds(
            userId,
            queryEmbedding,
            memoryType,
            scopeType,
            workspaceKey,
            sessionKey,
            resourceId,
            tags,
            MIN_CONFIDENCE_TO_STORE,
            MIN_IMPORTANCE_TO_STORE,
            limit
        );

        if (memoryIds.isEmpty()) {
            return recallByLocalEmbedding(
                userId,
                limit,
                queryEmbedding,
                memoryType,
                scopeType,
                workspaceKey,
                sessionKey,
                resourceId,
                tags
            );
        }

        Map<Long, Integer> orderById = new LinkedHashMap<>();
        for (int i = 0; i < memoryIds.size(); i++) {
            orderById.put(memoryIds.get(i), i);
        }

        return userMemoryRepository.findAllById(memoryIds).stream()
            .sorted(Comparator.comparing(memory -> orderById.get(memory.getId())))
            .toList();
    }

    private List<UserMemory> recallByLocalEmbedding(
        Long userId,
        int limit,
        List<Double> queryEmbedding,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        List<ScoredMemory> scoredMemories = findRecallCandidates(userId, memoryType, scopeType).stream()
            .filter(memory -> matchesMetadata(memory, workspaceKey, sessionKey, resourceId, tags))
            .filter(memory -> StringUtils.hasText(memory.getEmbeddingText()))
            .map(memory -> new ScoredMemory(
                memory,
                cosineSimilarity(queryEmbedding, parseEmbedding(memory.getEmbeddingText()))
            ))
            .sorted(Comparator
                .comparing(ScoredMemory::score)
                .thenComparing(scoredMemory -> scoredMemory.memory().getImportance())
                .reversed()
            )
            .limit(limit)
            .toList();

        if (scoredMemories.isEmpty()) {
            return recallByFilters(
                userId,
                limit,
                memoryType,
                scopeType,
                workspaceKey,
                sessionKey,
                resourceId,
                tags
            );
        }

        return scoredMemories.stream()
            .map(ScoredMemory::memory)
            .toList();
    }

    private List<UserMemory> recallByFilters(
        Long userId,
        int limit,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        return findRecallCandidates(userId, memoryType, scopeType).stream()
            .filter(memory -> matchesMetadata(memory, workspaceKey, sessionKey, resourceId, tags))
            .limit(limit)
            .toList();
    }

    private List<UserMemory> findRecallCandidates(
        Long userId,
        MemoryType memoryType,
        MemoryScopeType scopeType
    ) {
        return userMemoryRepository.findRecallCandidates(
            userId,
            MemoryStatus.ACTIVE,
            MIN_CONFIDENCE_TO_STORE,
            MIN_IMPORTANCE_TO_STORE,
            memoryType,
            scopeType,
            PageRequest.of(0, RECALL_FALLBACK_CANDIDATE_SIZE)
        );
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
        if (!isStorableScore(importance, confidence)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private boolean isStorableScore(Double importance, Double confidence) {
        return importance >= MIN_IMPORTANCE_TO_STORE && confidence >= MIN_CONFIDENCE_TO_STORE;
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

    private MemoryScopeType resolveScopeType(MemoryScopeType scopeType) {
        if (scopeType == null) {
            return MemoryScopeType.GLOBAL;
        }
        return scopeType;
    }

    private Map<String, Object> normalizeMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return Map.of();
        }
        return metadata;
    }

    private boolean matchesMetadata(
        UserMemory memory,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        Map<String, Object> metadata = memory.getMetadata();
        if (!matchesMetadataValue(metadata, "workspaceKey", workspaceKey)) {
            return false;
        }
        if (!matchesMetadataValue(metadata, "sessionKey", sessionKey)) {
            return false;
        }
        if (!matchesMetadataValue(metadata, "resourceId", resourceId)) {
            return false;
        }
        return matchesTags(metadata, tags);
    }

    private boolean matchesMetadataValue(Map<String, Object> metadata, String key, String expectedValue) {
        if (!StringUtils.hasText(expectedValue)) {
            return true;
        }
        if (metadata == null) {
            return false;
        }

        Object actualValue = metadata.get(key);
        return actualValue != null && expectedValue.trim().equals(actualValue.toString());
    }

    private boolean matchesTags(Map<String, Object> metadata, List<String> tags) {
        List<String> normalizedTags = tags == null ? List.of() : tags.stream()
            .filter(StringUtils::hasText)
            .map(String::trim)
            .toList();

        if (normalizedTags.isEmpty()) {
            return true;
        }
        if (metadata == null || !(metadata.get("tags") instanceof List<?> storedTags)) {
            return false;
        }

        List<String> normalizedStoredTags = storedTags.stream()
            .filter(Objects::nonNull)
            .map(Object::toString)
            .toList();

        return normalizedTags.stream().anyMatch(normalizedStoredTags::contains);
    }

    private String buildEmbeddingText(UserMemory memory) {
        return String.join(
            "\n",
            memory.getMemoryType().name(),
            memory.getScopeType().name(),
            nullToEmpty(memory.getSummary()),
            memory.getContent(),
            memory.getMetadata() == null ? "" : memory.getMetadata().toString()
        );
    }

    private List<Double> parseEmbedding(String embeddingText) {
        String trimmedText = embeddingText.replace("[", "").replace("]", "");
        if (!StringUtils.hasText(trimmedText)) {
            return List.of();
        }

        return List.of(trimmedText.split(",")).stream()
            .map(String::trim)
            .filter(StringUtils::hasText)
            .map(Double::parseDouble)
            .toList();
    }

    private double cosineSimilarity(List<Double> left, List<Double> right) {
        if (left.isEmpty() || right.isEmpty() || left.size() != right.size()) {
            return 0.0;
        }

        double dotProduct = 0.0;
        double leftNorm = 0.0;
        double rightNorm = 0.0;

        for (int i = 0; i < left.size(); i++) {
            double leftValue = left.get(i);
            double rightValue = right.get(i);
            dotProduct += leftValue * rightValue;
            leftNorm += leftValue * leftValue;
            rightNorm += rightValue * rightValue;
        }

        if (leftNorm == 0.0 || rightNorm == 0.0) {
            return 0.0;
        }
        return dotProduct / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm));
    }

    private record ScoredMemory(UserMemory memory, double score) {
    }

    private String nullToEmpty(String value) {
        if (value == null) {
            return "";
        }
        return value;
    }

    private String trimToNull(String value) {
        if (!StringUtils.hasText(value)) {
            return null;
        }
        return value.trim();
    }
}
