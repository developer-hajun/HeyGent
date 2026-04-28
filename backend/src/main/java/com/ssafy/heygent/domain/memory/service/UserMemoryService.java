package com.ssafy.heygent.domain.memory.service;

import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryCandidatesRequest;
import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.request.MarkMemoryUsedRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.embedding.MemoryEmbeddingService;
import com.ssafy.heygent.domain.memory.entity.MemoryOperationType;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
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
    private static final double MIN_RECALL_SIMILARITY = 0.35;
    private static final double MAX_RECALL_DISTANCE = 1.0 - MIN_RECALL_SIMILARITY;
    private static final double SEMANTIC_DUPLICATE_SIMILARITY = 0.92;

    private final UserMemoryRepository userMemoryRepository;
    private final UserMemoryVectorRepository userMemoryVectorRepository;
    private final MemoryEmbeddingService memoryEmbeddingService;
    private final MemorySafetyValidator memorySafetyValidator;

    @Transactional
    public UserMemoryResponse create(Long userId, CreateMemoryRequest request) {
        MemoryOperationType operationType = resolveOperationType(request.getOperationType());
        validateMemoryType(request.getMemoryType());
        validateMemoryScore(request.getImportance(), request.getConfidence());
        String normalizedContent = request.getContent().trim();
        Map<String, Object> metadata = normalizeMetadata(request.getMetadata(), request.getSourceSessionKey());
        memorySafetyValidator.validate(normalizedContent, request.getSummary(), metadata);
        memorySafetyValidator.validate(request.getEvidence(), request.getUpdateReason(), Map.of());
        MemoryStoreType storeType = resolveStoreType(request.getStoreType(), request.getMemoryType());
        MemoryScopeType scopeType = resolveScopeType(request.getScopeType(), storeType);
        validateStoreType(storeType, request.getMemoryType());
        validateSessionScope(scopeType, request.getExpiresAt());
        validateScopeMetadata(scopeType, metadata);
        validateValidityRange(request.getValidFrom(), request.getValidUntil());

        if (operationType == MemoryOperationType.INVALIDATE) {
            return invalidateTargetMemory(userId, request);
        }
        List<Double> embedding = memoryEmbeddingService.embed(buildEmbeddingText(
            storeType,
            request.getMemoryType(),
            scopeType,
            request.getSummary(),
            normalizedContent,
            request.getEvidence(),
            metadata
        ));
        if (operationType == MemoryOperationType.UPDATE || operationType == MemoryOperationType.MERGE) {
            return replaceTargetMemory(userId, request, storeType, scopeType, metadata, normalizedContent, embedding);
        }

        Optional<UserMemory> duplicateMemory = userMemoryRepository.findDuplicateActiveMemory(
                userId,
                storeType,
                request.getMemoryType(),
                scopeType,
                normalizedContent,
                MemoryStatus.ACTIVE
            )
            .filter(memory -> isNotExpired(memory, LocalDateTime.now()));
        if (duplicateMemory.isPresent()) {
            return UserMemoryResponse.from(duplicateMemory.get());
        }

        return findSemanticDuplicateMemory(
                userId,
                storeType,
                request.getMemoryType(),
                scopeType,
                metadata,
                embedding
            )
            .map(UserMemoryResponse::from)
            .orElseGet(() -> saveMemory(userId, request, storeType, scopeType, metadata, normalizedContent, embedding));
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
        MemoryStoreType storeType,
        MemoryScopeType scopeType,
        Map<String, Object> metadata,
        String normalizedContent,
        List<Double> embedding
    ) {

        UserMemory memory = UserMemory.builder()
            .userId(userId)
            .storeType(storeType)
            .memoryType(request.getMemoryType())
            .scopeType(scopeType)
            .content(normalizedContent)
            .summary(trimToNull(request.getSummary()))
            .metadata(metadata)
            .importance(request.getImportance())
            .confidence(request.getConfidence())
            .status(MemoryStatus.ACTIVE)
            .sourceSessionKey(trimToNull(request.getSourceSessionKey()))
            .sourceTaskRunId(trimToNull(request.getSourceTaskRunId()))
            .sourceMessageId(trimToNull(request.getSourceMessageId()))
            .evidence(trimToNull(request.getEvidence()))
            .updateReason(trimToNull(request.getUpdateReason()))
            .validFrom(resolveValidFrom(request.getValidFrom()))
            .validUntil(request.getValidUntil())
            .expiresAt(request.getExpiresAt())
            .build();

        UserMemory savedMemory = userMemoryRepository.save(memory);
        userMemoryVectorRepository.updateEmbedding(savedMemory.getId(), embedding);
        return UserMemoryResponse.from(savedMemory);
    }

    public List<UserMemoryResponse> getMyMemories(Long userId) {
        LocalDateTime now = LocalDateTime.now();
        return userMemoryRepository.findByUserIdAndStatusOrderByImportanceDescCreatedAtDesc(
                userId,
                MemoryStatus.ACTIVE
            )
            .stream()
            .filter(memory -> isNotExpired(memory, now))
            .map(UserMemoryResponse::from)
            .toList();
    }

    @Transactional
    public List<UserMemoryResponse> recall(
        Long userId,
        Integer limit,
        String query,
        MemoryStoreType storeType,
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
                storeType,
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
                storeType,
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
        MemoryStoreType storeType,
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
            storeType,
            memoryType,
            scopeType,
            workspaceKey,
            sessionKey,
            resourceId,
            tags,
            MIN_CONFIDENCE_TO_STORE,
            MIN_IMPORTANCE_TO_STORE,
            MAX_RECALL_DISTANCE,
            limit
        );

        if (memoryIds.isEmpty()) {
            return recallByLocalEmbedding(
                userId,
                limit,
                queryEmbedding,
                storeType,
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
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        List<ScoredMemory> scoredMemories = findRecallCandidates(userId, storeType, memoryType, scopeType).stream()
            .filter(memory -> matchesMetadata(memory, workspaceKey, sessionKey, resourceId, tags))
            .filter(memory -> StringUtils.hasText(memory.getEmbeddingText()))
            .map(memory -> new ScoredMemory(
                memory,
                cosineSimilarity(queryEmbedding, parseEmbedding(memory.getEmbeddingText()))
            ))
            .filter(scoredMemory -> scoredMemory.score() >= MIN_RECALL_SIMILARITY)
            .sorted(Comparator
                .comparing(ScoredMemory::score)
                .thenComparing(scoredMemory -> scoredMemory.memory().getImportance())
                .reversed()
            )
            .limit(limit)
            .toList();

        return scoredMemories.stream()
            .map(ScoredMemory::memory)
            .toList();
    }

    private List<UserMemory> recallByFilters(
        Long userId,
        int limit,
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags
    ) {
        return findRecallCandidates(userId, storeType, memoryType, scopeType).stream()
            .filter(memory -> matchesMetadata(memory, workspaceKey, sessionKey, resourceId, tags))
            .limit(limit)
            .toList();
    }

    private List<UserMemory> findRecallCandidates(
        Long userId,
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType
    ) {
        return userMemoryRepository.findRecallCandidates(
            userId,
            MemoryStatus.ACTIVE,
            MIN_CONFIDENCE_TO_STORE,
            MIN_IMPORTANCE_TO_STORE,
            LocalDateTime.now(),
            storeType,
            memoryType,
            scopeType,
            MemoryScopeType.SESSION,
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

    @Transactional
    public UserMemoryResponse markUsed(Long userId, Long memoryId, MarkMemoryUsedRequest request) {
        UserMemory memory = findOwnedMemory(userId, memoryId);
        if (memory.getStatus() != MemoryStatus.ACTIVE || !isNotExpired(memory, LocalDateTime.now())) {
            throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
        }

        memory.markUsed(LocalDateTime.now(), request.getUsefulnessScore());
        return UserMemoryResponse.from(memory);
    }

    private UserMemoryResponse replaceTargetMemory(
        Long userId,
        CreateMemoryRequest request,
        MemoryStoreType storeType,
        MemoryScopeType scopeType,
        Map<String, Object> metadata,
        String normalizedContent,
        List<Double> embedding
    ) {
        UserMemory targetMemory = findOwnedMemory(userId, request.getTargetMemoryId());
        validateTargetCanChange(targetMemory);

        UserMemoryResponse savedResponse = saveMemory(
            userId,
            request,
            storeType,
            scopeType,
            metadata,
            normalizedContent,
            embedding
        );
        targetMemory.invalidate(savedResponse.getId(), trimToNull(request.getUpdateReason()), LocalDateTime.now());
        return savedResponse;
    }

    private Optional<UserMemory> findSemanticDuplicateMemory(
        Long userId,
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        Map<String, Object> metadata,
        List<Double> embedding
    ) {
        return findRecallCandidates(userId, storeType, memoryType, scopeType).stream()
            .filter(memory -> hasSameMemoryBoundary(memory.getMetadata(), metadata))
            .filter(memory -> StringUtils.hasText(memory.getEmbeddingText()))
            .map(memory -> new ScoredMemory(
                memory,
                cosineSimilarity(embedding, parseEmbedding(memory.getEmbeddingText()))
            ))
            .filter(scoredMemory -> scoredMemory.score() >= SEMANTIC_DUPLICATE_SIMILARITY)
            .sorted(Comparator
                .comparing(ScoredMemory::score)
                .thenComparing(scoredMemory -> scoredMemory.memory().getImportance())
                .reversed()
            )
            .map(ScoredMemory::memory)
            .findFirst();
    }

    private boolean hasSameMemoryBoundary(Map<String, Object> storedMetadata, Map<String, Object> newMetadata) {
        return hasSameMetadataValue(storedMetadata, newMetadata, "workspaceKey")
            && hasSameMetadataValue(storedMetadata, newMetadata, "sessionKey")
            && hasSameMetadataValue(storedMetadata, newMetadata, "resourceId");
    }

    private boolean hasSameMetadataValue(Map<String, Object> storedMetadata, Map<String, Object> newMetadata, String key) {
        Object storedValue = storedMetadata == null ? null : storedMetadata.get(key);
        Object newValue = newMetadata == null ? null : newMetadata.get(key);
        if (storedValue == null && newValue == null) {
            return true;
        }
        if (storedValue == null || newValue == null) {
            return false;
        }
        return storedValue.toString().equals(newValue.toString());
    }

    private UserMemoryResponse invalidateTargetMemory(Long userId, CreateMemoryRequest request) {
        UserMemory targetMemory = findOwnedMemory(userId, request.getTargetMemoryId());
        validateTargetCanChange(targetMemory);
        targetMemory.invalidate(null, trimToNull(request.getUpdateReason()), LocalDateTime.now());
        return UserMemoryResponse.from(targetMemory);
    }

    private UserMemory findOwnedMemory(Long userId, Long memoryId) {
        if (memoryId == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        UserMemory memory = userMemoryRepository.findById(memoryId)
            .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        if (!memory.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.ACCESS_DENIED);
        }
        return memory;
    }

    private void validateTargetCanChange(UserMemory memory) {
        if (memory.getStatus() == MemoryStatus.DELETED || memory.getStatus() == MemoryStatus.INACTIVE) {
            throw new CustomException(ErrorCode.RESOURCE_NOT_FOUND);
        }
    }

    private void validateMemoryScore(Double importance, Double confidence) {
        if (!isStorableScore(importance, confidence)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private boolean isStorableScore(Double importance, Double confidence) {
        return importance >= MIN_IMPORTANCE_TO_STORE && confidence >= MIN_CONFIDENCE_TO_STORE;
    }

    private MemoryOperationType resolveOperationType(MemoryOperationType operationType) {
        if (operationType == null) {
            return MemoryOperationType.ADD;
        }
        return operationType;
    }

    private void validateMemoryType(MemoryType memoryType) {
        if (memoryType == MemoryType.PROJECT_CONTEXT) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private MemoryStoreType resolveStoreType(MemoryStoreType storeType, MemoryType memoryType) {
        if (storeType != null) {
            return storeType;
        }
        if (memoryType == MemoryType.PROFILE || memoryType == MemoryType.PREFERENCE) {
            return MemoryStoreType.USER_PROFILE;
        }
        return MemoryStoreType.AGENT_MEMORY;
    }

    private void validateStoreType(MemoryStoreType storeType, MemoryType memoryType) {
        if (storeType == MemoryStoreType.USER_PROFILE
            && memoryType != MemoryType.PROFILE
            && memoryType != MemoryType.PREFERENCE) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        if (storeType == MemoryStoreType.AGENT_MEMORY
            && (memoryType == MemoryType.PROFILE || memoryType == MemoryType.PREFERENCE)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private void validateSessionScope(MemoryScopeType scopeType, LocalDateTime expiresAt) {
        if (scopeType != MemoryScopeType.SESSION) {
            return;
        }
        if (expiresAt == null || !expiresAt.isAfter(LocalDateTime.now())) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private void validateScopeMetadata(MemoryScopeType scopeType, Map<String, Object> metadata) {
        if (scopeType == MemoryScopeType.WORKSPACE) {
            validateRequiredMetadata(metadata, "workspaceKey");
            return;
        }
        if (scopeType == MemoryScopeType.RESOURCE) {
            validateRequiredMetadata(metadata, "resourceId");
            return;
        }
        if (scopeType == MemoryScopeType.SESSION) {
            validateRequiredMetadata(metadata, "sessionKey");
        }
    }

    private void validateRequiredMetadata(Map<String, Object> metadata, String key) {
        if (metadata == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        Object value = metadata.get(key);
        if (value == null || !StringUtils.hasText(value.toString())) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
    }

    private void validateValidityRange(LocalDateTime validFrom, LocalDateTime validUntil) {
        if (validFrom == null || validUntil == null) {
            return;
        }
        if (!validUntil.isAfter(validFrom)) {
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

    private MemoryScopeType resolveScopeType(MemoryScopeType scopeType, MemoryStoreType storeType) {
        if (scopeType == null) {
            return MemoryScopeType.GLOBAL;
        }
        return scopeType;
    }

    private Map<String, Object> normalizeMetadata(Map<String, Object> metadata, String sourceSessionKey) {
        Map<String, Object> normalizedMetadata = new LinkedHashMap<>();
        if (metadata != null && !metadata.isEmpty()) {
            normalizedMetadata.putAll(metadata);
        }
        if (StringUtils.hasText(sourceSessionKey) && !normalizedMetadata.containsKey("sessionKey")) {
            normalizedMetadata.put("sessionKey", sourceSessionKey.trim());
        }
        if (normalizedMetadata.isEmpty()) {
            return Map.of();
        }
        return normalizedMetadata;
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

    private boolean isNotExpired(UserMemory memory, LocalDateTime now) {
        return isCurrentlyValid(memory, now) && (memory.getExpiresAt() == null || memory.getExpiresAt().isAfter(now));
    }

    private boolean isCurrentlyValid(UserMemory memory, LocalDateTime now) {
        boolean started = memory.getValidFrom() == null || !memory.getValidFrom().isAfter(now);
        boolean notEnded = memory.getValidUntil() == null || memory.getValidUntil().isAfter(now);
        return started && notEnded;
    }

    private String buildEmbeddingText(UserMemory memory) {
        return buildEmbeddingText(
            memory.getStoreType(),
            memory.getMemoryType(),
            memory.getScopeType(),
            memory.getSummary(),
            memory.getContent(),
            memory.getEvidence(),
            memory.getMetadata()
        );
    }

    private String buildEmbeddingText(
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String summary,
        String content,
        String evidence,
        Map<String, Object> metadata
    ) {
        return String.join(
            "\n",
            storeType.name(),
            memoryType.name(),
            scopeType.name(),
            nullToEmpty(summary),
            content,
            nullToEmpty(evidence),
            metadata == null ? "" : metadata.toString()
        );
    }

    private LocalDateTime resolveValidFrom(LocalDateTime validFrom) {
        if (validFrom == null) {
            return LocalDateTime.now();
        }
        return validFrom;
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
