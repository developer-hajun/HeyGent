package com.ssafy.heygent.domain.memory.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.embedding.MemoryEmbeddingService;
import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.entity.MemoryOperationType;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;
import com.ssafy.heygent.domain.memory.repository.UserMemoryRepository;
import com.ssafy.heygent.domain.memory.repository.UserMemoryVectorRepository;
import com.ssafy.heygent.global.exception.CustomException;

@ExtendWith(MockitoExtension.class)
class UserMemoryPolicyQualityTest {

    private static final Long USER_ID = 1L;

    @Mock
    private UserMemoryRepository userMemoryRepository;

    @Mock
    private UserMemoryVectorRepository userMemoryVectorRepository;

    @Mock
    private MemoryEmbeddingService memoryEmbeddingService;

    @Mock
    private MemorySafetyValidator memorySafetyValidator;

    @Mock
    private UserMemoryEventService userMemoryEventService;

    @InjectMocks
    private UserMemoryService userMemoryService;

    @Test
    void createResourceMemoryWithoutResourceIdFails() {
        CreateMemoryRequest request = createRequest(MemoryType.FACT, MemoryScopeType.RESOURCE, Map.of());

        assertThatThrownBy(() -> userMemoryService.create(USER_ID, request))
            .isInstanceOf(CustomException.class);

        verify(memoryEmbeddingService, never()).embed(anyString());
        verify(userMemoryRepository, never()).save(any(UserMemory.class));
    }

    @Test
    void createSessionMemoryUsesSourceSessionKeyAsMetadata() {
        CreateMemoryRequest request = createRequest(MemoryType.FACT, MemoryScopeType.SESSION, Map.of());
        ReflectionTestUtils.setField(request, "sourceSessionKey", "session-1");
        ReflectionTestUtils.setField(request, "expiresAt", LocalDateTime.now().plusHours(1));

        when(memoryEmbeddingService.embed(anyString())).thenReturn(List.of(0.1, 0.2));
        when(userMemoryRepository.findDuplicateActiveMemory(
            eq(USER_ID),
            eq(MemoryStoreType.AGENT_MEMORY),
            eq(MemoryType.FACT),
            eq(MemoryScopeType.SESSION),
            eq("사용자는 짧은 답변을 선호한다."),
            eq(MemoryStatus.ACTIVE)
        )).thenReturn(Optional.empty());
        when(userMemoryRepository.findRecallCandidates(
            eq(USER_ID),
            eq(MemoryStatus.ACTIVE),
            anyDouble(),
            anyDouble(),
            any(LocalDateTime.class),
            eq(MemoryStoreType.AGENT_MEMORY),
            eq(MemoryType.FACT),
            eq(MemoryScopeType.SESSION),
            eq(MemoryScopeType.SESSION),
            any(Pageable.class)
        )).thenReturn(List.of());
        when(userMemoryRepository.save(any(UserMemory.class))).thenAnswer(invocation -> {
            UserMemory memory = invocation.getArgument(0);
            ReflectionTestUtils.setField(memory, "id", 10L);
            return memory;
        });

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getMetadata()).containsEntry("sessionKey", "session-1");
        verify(userMemoryEventService).record(any(UserMemory.class), eq(MemoryEventType.CREATED));
    }

    @Test
    void updatePreferenceInvalidatesPreviousMemoryAndCreatesUpdatedMemory() {
        CreateMemoryRequest request = createRequest(MemoryType.PREFERENCE, MemoryScopeType.GLOBAL, Map.of());
        ReflectionTestUtils.setField(request, "operationType", MemoryOperationType.UPDATE);
        ReflectionTestUtils.setField(request, "targetMemoryId", 20L);
        ReflectionTestUtils.setField(request, "content", "사용자는 이제 짧은 답변을 선호한다.");
        ReflectionTestUtils.setField(request, "updateReason", "사용자 선호 변경");
        UserMemory targetMemory = memory(20L, MemoryType.PREFERENCE, MemoryScopeType.GLOBAL, "사용자는 긴 답변을 선호한다.");

        when(memoryEmbeddingService.embed(anyString())).thenReturn(List.of(0.1, 0.2));
        when(userMemoryRepository.findById(20L)).thenReturn(Optional.of(targetMemory));
        when(userMemoryRepository.save(any(UserMemory.class))).thenAnswer(invocation -> {
            UserMemory memory = invocation.getArgument(0);
            ReflectionTestUtils.setField(memory, "id", 21L);
            return memory;
        });

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getId()).isEqualTo(21L);
        assertThat(targetMemory.getStatus()).isEqualTo(MemoryStatus.INACTIVE);
        assertThat(targetMemory.getSupersededByMemoryId()).isEqualTo(21L);
        assertThat(targetMemory.getUpdateReason()).isEqualTo("사용자 선호 변경");
        verify(userMemoryEventService).record(any(UserMemory.class), eq(MemoryEventType.UPDATED));
        verify(userMemoryEventService).record(
            eq(targetMemory),
            eq(MemoryEventType.INVALIDATED),
            eq(null),
            eq(Map.of("supersededByMemoryId", 21L, "operationType", MemoryEventType.UPDATED.name()))
        );
    }

    @Test
    void getMyMemoriesExcludesExpiredMemory() {
        UserMemory validMemory = memory(30L, MemoryType.FACT, MemoryScopeType.GLOBAL, "현재 유효한 기억");
        UserMemory expiredMemory = memory(31L, MemoryType.FACT, MemoryScopeType.GLOBAL, "만료된 기억");
        ReflectionTestUtils.setField(expiredMemory, "expiresAt", LocalDateTime.now().minusMinutes(1));
        when(userMemoryRepository.findByUserIdAndStatusOrderByImportanceDescCreatedAtDesc(
            USER_ID,
            MemoryStatus.ACTIVE
        )).thenReturn(List.of(validMemory, expiredMemory));

        List<UserMemoryResponse> responses = userMemoryService.getMyMemories(USER_ID);

        assertThat(responses)
            .extracting(UserMemoryResponse::getId)
            .containsExactly(30L);
    }

    @Test
    void recallFiltersByWorkspaceMetadata() {
        UserMemory matchingMemory = memory(40L, MemoryType.FACT, MemoryScopeType.WORKSPACE, "워크스페이스 A 기억");
        UserMemory otherMemory = memory(41L, MemoryType.FACT, MemoryScopeType.WORKSPACE, "워크스페이스 B 기억");
        ReflectionTestUtils.setField(matchingMemory, "metadata", Map.of("workspaceKey", "workspace-a"));
        ReflectionTestUtils.setField(otherMemory, "metadata", Map.of("workspaceKey", "workspace-b"));
        when(userMemoryRepository.findRecallCandidates(
            eq(USER_ID),
            eq(MemoryStatus.ACTIVE),
            anyDouble(),
            anyDouble(),
            any(LocalDateTime.class),
            eq(MemoryStoreType.AGENT_MEMORY),
            eq(MemoryType.FACT),
            eq(MemoryScopeType.WORKSPACE),
            eq(MemoryScopeType.SESSION),
            any(Pageable.class)
        )).thenReturn(List.of(matchingMemory, otherMemory));

        List<UserMemoryResponse> responses = userMemoryService.recall(
            USER_ID,
            5,
            null,
            MemoryStoreType.AGENT_MEMORY,
            MemoryType.FACT,
            MemoryScopeType.WORKSPACE,
            "workspace-a",
            null,
            null,
            null,
            null
        );

        assertThat(responses)
            .extracting(UserMemoryResponse::getId)
            .containsExactly(40L);
    }

    private CreateMemoryRequest createRequest(
        MemoryType memoryType,
        MemoryScopeType scopeType,
        Map<String, Object> metadata
    ) {
        CreateMemoryRequest request = new CreateMemoryRequest();
        ReflectionTestUtils.setField(request, "memoryType", memoryType);
        ReflectionTestUtils.setField(request, "scopeType", scopeType);
        ReflectionTestUtils.setField(request, "content", "사용자는 짧은 답변을 선호한다.");
        ReflectionTestUtils.setField(request, "summary", "짧은 답변 선호");
        ReflectionTestUtils.setField(request, "metadata", metadata);
        ReflectionTestUtils.setField(request, "importance", 0.8);
        ReflectionTestUtils.setField(request, "confidence", 0.9);
        return request;
    }

    private UserMemory memory(
        Long id,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String content
    ) {
        return UserMemory.builder()
            .id(id)
            .userId(USER_ID)
            .storeType(resolveStoreType(memoryType))
            .memoryType(memoryType)
            .scopeType(scopeType)
            .content(content)
            .summary(content)
            .metadata(Map.of())
            .embeddingText("[0.1,0.2]")
            .importance(0.8)
            .confidence(0.9)
            .status(MemoryStatus.ACTIVE)
            .validFrom(LocalDateTime.now().minusDays(1))
            .accessCount(0L)
            .usedCount(0L)
            .usefulnessScore(0.0)
            .build();
    }

    private MemoryStoreType resolveStoreType(MemoryType memoryType) {
        if (memoryType == MemoryType.PROFILE || memoryType == MemoryType.PREFERENCE) {
            return MemoryStoreType.USER_PROFILE;
        }
        return MemoryStoreType.AGENT_MEMORY;
    }
}
